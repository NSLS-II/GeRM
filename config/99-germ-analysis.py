import dask.array as da

# grab ts and td
#hdr = db['280c99d4-88de-4958-85fb-1c44e1bc40bd']
#hdr = db['280c99d4-88de-4958-85fb-1c44e1bc40bd']
#hdr = db['e9e6eae9-d273-41df-be42-27b7de6874bd']
# test
#uid = 'a3fdc686'
# intersting data set
uid='c8b6e2b6'

# uid '7fcb8fe6'
hdr = db[uid]
# TODO choose more than one event
evts = iter(hdr.events(fill=True))

# max chunk size
NMAX = 100000
T_START = 1000000
print("Choosing events {} to {}".format(T_START, T_START+NMAX))
#NCHUNKS = 1000

evt = next(evts)
dat = evt['data']
print("Found {} events".format(len(dat['germ_chip'])))
# get first event only so far
#tab = hdr.table(fill=True)
allowed_keys = ['germ_chip', 'germ_chan', 'germ_td', 'germ_pd', 'germ_ts']
for key in dat.keys():
    if key in allowed_keys:
        dat[key] = dat[key][T_START:NMAX+T_START].astype(np.uint32)
        #dat[key] = (dat[key], NCHUNKS).astype(np.uint32)

germ_ts = dat['germ_ts']
germ_td = dat['germ_td']
germ_pd = dat['germ_pd']
germ_chip = dat['germ_chip']
germ_chan = dat['germ_chan']

# truncate arrays
#germ_ts = germ_ts[T_START:NMAX+T_START]
#germ_td = germ_td[T_START:NMAX+T_START]
#germ_pd = germ_pd[T_START:NMAX+T_START]
#germ_chip= germ_chip[T_START:NMAX+T_START]
#germ_chan = germ_chan[T_START:NMAX+T_START]


# make dask arrays
#germ_ts = da.from_array(germ_ts, chunks=100)
#germ_td = da.from_array(germ_td, chunks=100)
#germ_pd = da.from_array(germ_pd, chunks=100)
#germ_chip = da.from_array(germ_chip, chunks=100)
#germ_chan = da.from_array(germ_chan, chunks=100)

RESOLUTION = 40e-9 # seconds per clock cycle

def fix_time(ts):	
    ''' Fix the time in clock cycles from the FPGA 
        taking into account the wrap.
        ts : time (in clock cyles)
            NOTE : edits in place

        globals:
            JUMP : the max number of clock cycles measured before jump
            THRESH :
                set some minimum threshold to detect the jump
                don't want to add a jump at every negative diff
                since the time stamps don't arrive exactly in order
                (I was told it's on the order of 12 clock cyles, much less
                less than my aggressive threhsold of 2**26)
    '''
    # copy and ensure it's int
    #ts = ts.copy().astype(int)

    # the jump is currently 2**27 (27 bits for clock ticks)
    JUMP = 2**27
    THRESH = 2**26

    # time differences
    ts_diff = np.diff(ts)

    # find the regions where it's negative
    # this should just be a few (1, 2 dozen maybe?)
    w, = np.where(ts_diff < -THRESH)
    if len(w) > 10:
        print("Warning, detected more than 10 jumps? (long measurement maybe?)")
        print("Detected {} jumps".format(len(w)))
    njumps = 0
    for ind in w:
        njumps += 1
        ts[ind+1:] += JUMP

    return njumps

    
# for for jump in time
# fixes array in place
njumps = fix_time(germ_ts)
# now sort in increasing order (because they're not exactly increasing)
sort_ind = np.argsort(germ_ts)
# and sort
germ_ts = germ_ts[sort_ind]
germ_td = germ_td[sort_ind]
germ_pd = germ_pd[sort_ind]
germ_chip = germ_chip[sort_ind]
germ_chan = germ_chan[sort_ind]

# debugging
#plt.figure(2);plt.clf();plt.plot(germ_ts)
#plt.pause(.0001)
#input("check and confirm")

tot_time = (germ_ts[-1]-germ_ts[0])*RESOLUTION
print("Data is {}s long".format(tot_time))


# now filter by time in seconds
#time_delta = .1 # .1 s
#time_delta_clocks = int(time_delta/RESOLUTION)

# set to zero
germ_ts_delta = germ_ts-germ_ts[0]
# integer division for bins
#germ_ts_delta_clocks = germ_ts_delta / time_delta_clocks

n_chans =32

chip_index = germ_chip*n_chans + germ_chan
germ_pd_index = germ_pd
time_index = germ_ts_delta #ids
time_index = time_index*RESOLUTION

# correct for the energy
#corr_mat = 

MAX_CHIP = np.max(chip_index)
MAX_TIME = np.max(time_index)
MAX_PD = 4096-1

# chunk into 100 times
N_TIMES = 100

N_ENERGY = 4096
MAX_ENERGY = 70

from skbeam.core.accumulators.histogram import Histogram

hh = Histogram((MAX_CHIP+1, 0, MAX_CHIP+1),
               #(MAX_PD+1, 0, MAX_PD+1),
               (N_ENERGY, 0, MAX_ENERGY),
               (N_TIMES, 0, MAX_TIME), 
)
# energy array calibrated
#eng_arr = gpd*corr_mat[0, i] + corr_mat[1, i]


#_cal_file = Path(os.path.realpath(__file__)).parent / 'calibration_matrix_20171130.txt'
_cal_file = '/home/xf28id1/.ipython/profile_collection_germ/startup/data/calibration_matrix_20171130.txt'
cal_val = np.loadtxt(str(_cal_file))
eng_arr = germ_pd*cal_val[0, chip_index] + cal_val[1, chip_index]


hh.fill(chip_index, eng_arr, time_index)
h_extent = (hh.edges[1][0], hh.edges[1][-1], hh.edges[0][-1], hh.edges[0][0])
#bind = MAX_TIME*MAX_CHIP*pd_index  + MAX_CHIP*time_index + chip_index

#res = np.bincount(bind, germ_pd)

#hmap, _ = make_mars_heatmap_after_correction(hdr)

from pylab import *
ion()

figure(10);clf()
imshow(hh.values[:,:, 0], aspect='auto', vmin=0, vmax=1000)

#figure(11);clf()
#imshow(hmap.T, aspect='auto', vmin=0, vmax=1000)

# checked without correction that histograms were same and they were so it works
#figure(12);clf()
#imshow(np.abs(hh.values[:,:, 0] - hmap.T), vmax=100, aspect='auto')

h_energies = hh.centers[1]
energy_limits = [30,60]
energy_inds, = np.where((h_energies > energy_limits[0])*\
                       (h_energies < energy_limits[1]))

h_lines = np.sum(hh.values[:,energy_inds,:], axis=1)

figure(13);clf();
imshow(h_lines, aspect='auto',
        extent=(hh.centers[2][0], hh.centers[2][-1], hh.centers[0][-1], hh.centers[0][0]))
xlabel("time (s)")
ylabel("channel #")

#print('values : {}'.format(np.sum(np.abs(hh.values - hmap.T))))
for i in range(hh.values.shape[2]):
    figure(12);
    clf();imshow(hh.values[:,:, i], aspect='auto', vmin=0, vmax=10, extent=h_extent)

    #figure(13);clf()
    pause(.0001)
    #print(i)

