'''
    Tools for reducing GeRM data.

    Note that this strongly relies on the data format for the following
    reasons:
        1. The times (in ns) wrap around due to overflow in the register that
            stores it
        2. A calibration matrix is needed to convert ADU's to keV (or other)
        3. Data positions are returned in chip, chan coordinates, which
            need to be remapped to a 1D array (since it's 1D in q space).

'''
import numpy as np
import matplotlib.pyplot as plt
from skbeam.core.accumulators.histogram import Histogram

def fix_time(ts, njumps=0, jump=2**29, thresh=2**26):
    ''' Fix the time in clock cycles from the FPGA

        This is necessary unfortunately when cycling through GeRM data. This
        takes into account the wrap in time.
        The time will wrap at jump = 2**bits where bits is the number of bits
        for the time stamp.

        Normally, this is as straightforward as detecting when the next time
        stamp wraps back to zero. Unfortunately, the timestamps don't quite
        come in the right order. Due to this extra complication, we need add a
        trick where we only correct when we notice a huge difference in times.

        This helps correct for when time deltas are small.

        However, this currently does *not* correct for the one odd case where
        the time could wrap around, then come back, then wrap around again due
        to things out of order. This *should* be fixed in the future. It's not
        clear whether this will be done in hardware or software.

        NOTE :
            since this depends on time differences, if moving through an
            array, always give a previous value. For ex:
            res, njumps = fix_time(arr[:100], njumps=0)
            res2 = fix_time(arr[100-1:100-1+1], njumps=njumps)

        Parameters
        ----------

        ts : time (in clock cyles)

        njumps : the previous number of jumps in time

        jump : the max number of clock cycles measured before jump
            currently 2**29 (29 bits)

        thresh :
            set some minimum threshold to detect the jump
            don't want to add a jump at every negative diff
            since the time stamps don't arrive exactly in order
            (I was told it's on the order of 12 clock cyles, much less
            less than my aggressive threhsold of 2**26)
    '''
    # if it's dask array compute it
    if hasattr(ts, 'compute'):
        ts = ts.astype(int).compute()
    else:
        # else just copy
        ts = ts.copy().astype(int)

    # if there is a baseline to add, add it
    # (for the overflow)
    # don't increment the overlap
    if njumps > 0:
        ts += njumps*jump

    # time differences
    ts_diff = np.diff(ts)


    # find the regions where it's negative
    # this should just be a few (1, 2 dozen maybe?)
    # do abs so we can find quick ups and downs
    w, = np.where(np.abs(ts_diff) > thresh)
    if len(w) > 10:
        print("Warning, detected more than 10 jumps? (long measurement maybe?)")
        print("Detected {} jumps".format(len(w)))
    if len(w) > 0:
        print("Jumps at {}".format(w))

    for ind in w:
        njumps += 1
        # when goes negative should change sign
        if (ts_diff[ind] > thresh):
            print("Found a positive sign case, subtracting again")
        sgn = 1 - 2*(ts_diff[ind] > thresh)
        ts[ind+1:] += jump*sgn

    return ts, njumps


def histogram_germ(germ_ts, germ_td, germ_pd, germ_chip, germ_chan,
                   time_resolution, start_time, end_time,
                   energy_resolution, min_energy, max_energy,
                   calibration = None,
                   td_resolution=40e-9, n_chans=32, n_chips=12,
                   jump_bits=29, thresh_bits=26,
                   chunksize=1000000,
                   plot=True, verbose=False):
    '''
        Histogram the GeRM data.

        Parameters
        ----------

        germ_ts : dask.array or np.ndarray
            timestamp in seconds
        germ_td : dask.array or np.ndarray
            timestamp in clock cycles
        germ_pd : dask.array or np.ndarray
            the germ data
        germ_chip : dask.array or np.ndarray
            the channel number
        germ_chan : dask.array or np.ndarray
            the chip number

        time_resolution: the time to bin by
        start_time : the start time
        end_time : the stop time

        energy_resolution: int
            the number of energies to count on
        min_energy: float
            the minimum energy to measure up to
        max_energy: float
            the maximum energy to measure up to

        td_resolution: float
            the time resolution of each count in germ_td in seconds
        n_chans: int
            the number of channels
        n_chips : int
            the number of chips

        calibration: 2d np.ndarray
            calibration matrix for the data
            It should be a 2d array of dimensions 2 x (n_chips*n_chans + 1)
            It specifies an interpolation of the form:
                res = res*cal[0, loc] + cal[1, loc]

        jump_bits: int
            Don't change this unless you know what you're doing
            (see fixtime)

        thresh_bits: int
            Don't change this unless you know what you're doing
            (see fixtime)

        chunksize: int
            The number of chunks of data to read.
            Note: specify this for large data sets that can't fit into memory!
            Keep increasing until it fits. The smaller the chunksize, the
            slower the analysis (more iterations required).

        verbose: bool, optional
            print more verbose flags if needed

        Notes
        -----
            Either *all* of [germ_ts, germ_td, germ_pd, germ_chip, germ_chan]
            are dask arrays or *None* are dask arrays.

        Returns
        -------
        spectrum : 3d np.ndarray
            This is a histogram of by chip x energy x time

        spectrum_edges: list of 3 1d np.ndarrays
            List of three edges, in order:
                - the chips (useful for verification that the edges are correct,
                should be integers)
                - the energies (should be in units of keV)
                    note: a proper calibration matrix must be used to properly
                    convert from ADU to keV. Else, the result is not keV
                - the times (in s)

    '''
    if hasattr(germ_ts, 'compute'):
        using_dask = True
    else:
        using_dask = False

    if calibration is not None:
        calA = calibration[0,:]
        calB = calibration[1,:]
    else:
        print("Calibration not set. Histogram will be over ADU's")

    # prepare the histogram binning vals
    max_chip = n_chips*n_chans
    n_chips = max_chip + 1

    n_energy = int((max_energy- min_energy)/energy_resolution)
    n_times = int((end_time-start_time)/time_resolution)

    hh = Histogram((n_chips, 0, n_chips),
                   (n_energy, min_energy, max_energy),
                   (n_times, start_time, end_time),
                   )

    h_energies = hh.centers[1]

    Nreads = len(germ_ts)//chunksize
    njumps = 0

    Nbins = 400
    tot_hist = np.zeros((Nreads, Nbins))

    jump_val = 2**jump_bits
    thresh_val = 2**thresh_bits

    for i in range(Nreads):
        print("running {} of {}".format(i, Nreads))
        if i == 0:
            germ_ts_chunk, njumps = fix_time(germ_ts[i*chunksize:(i+1)*chunksize], njumps=njumps, jump=jump_val, thresh=thresh_val)
        else:
            # pass the before last value
            germ_ts_chunk, njumps = fix_time(germ_ts[i*chunksize-1:(i+1)*chunksize], njumps=njumps, jump=jump_val, thresh=thresh_val)
            germ_ts_chunk = germ_ts_chunk[1:]

        # now slice the rest
        chunkslice = slice(i*chunksize, (i+1)*chunksize)
        germ_td_chunk = germ_td[chunkslice]
        germ_pd_chunk = germ_pd[chunkslice]
        germ_chip_chunk = germ_chip[chunkslice]
        germ_chan_chunk = germ_chan[chunkslice]

        if using_dask:
            hh_np, bin_edges = np.histogram(germ_pd_chunk.compute(), bins=Nbins)
        else:
            hh_np, bin_edges = np.histogram(germ_pd_chunk, bins=Nbins)

        tot_hist[i] = hh_np

        sort_ind = np.argsort(germ_ts_chunk)
        germ_ts_chunk = germ_ts_chunk[sort_ind].astype(np.int)
        if using_dask:
            germ_td_chunk = germ_td_chunk[sort_ind].compute().astype(np.int)
            germ_pd_chunk = germ_pd_chunk[sort_ind].compute().astype(np.int)
            germ_chip_chunk = germ_chip_chunk[sort_ind].compute().astype(np.int)
            germ_chan_chunk = germ_chan_chunk[sort_ind].compute().astype(np.int)
        else:
            germ_td_chunk = germ_td_chunk[sort_ind].astype(np.int)
            germ_pd_chunk = germ_pd_chunk[sort_ind].astype(np.int)
            germ_chip_chunk = germ_chip_chunk[sort_ind].astype(np.int)
            germ_chan_chunk = germ_chan_chunk[sort_ind].astype(np.int)

        time_delta = germ_ts_chunk[-1] - germ_ts_chunk[0]
        time_delta = time_delta*td_resolution
        #print("time delta for this slice is {}s".format(time_delta))
        #print("njumps : {}".format(njumps))



        # convert chip chan to pos
        germ_pos_chunk = germ_chip_chunk*n_chans + germ_chan_chunk
        if using_dask:
            germ_ts0 = germ_ts[0].compute()
        else:
            germ_ts0 = germ_ts[0]

        germ_t0 = germ_ts0*td_resolution

        germ_time_chunk = (germ_ts_chunk - germ_ts0)*td_resolution

        if calibration is not None:
            germ_pd_chunk_corrected = germ_pd_chunk*calA[germ_pos_chunk] + calB[germ_pos_chunk]
        else:
            germ_pd_chunk_corrected = germ_pd_chunk


        # filling histogram
        print("Filling histogram")
        print(f"Energies: {germ_pd_chunk_corrected}")
        hh.fill(germ_pos_chunk, germ_pd_chunk_corrected, germ_time_chunk)
        #raise

        # plotting now
        h_lines = np.sum(hh.values[:,:,:], axis=1)
        if plot:
            plt.figure(13);plt.clf();
            plt.imshow(h_lines, aspect='auto',
                    extent=(hh.centers[2][0], hh.centers[2][-1], hh.centers[0][-1], hh.centers[0][0]))
            plt.xlabel("time (s)")
            plt.ylabel("channel #")
            plt.pause(.0001)

    return hh.values, hh.centers


def fit_lines():
