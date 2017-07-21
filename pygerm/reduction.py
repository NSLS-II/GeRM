import pandas as pd
import numpy as np


def bin_frame(data, bins, corr_mat=None):
    """Bin a single GeRM frame to Energy/ADU vs channel spectrum

    # TODO bin on other channel
    # TODO make energy range configurable
    # TODO select chips / channels

    Parameters
    ----------
    data : dict
        must have the keys {'germ_chip', 'germ_chan', 'germ_pd'}

    bins : int or sequence
       If int, use bins bins between 0 and 70.  If a sequence, is
       bin edges (including right edge) as with `np.histogram`

    corr_mat : array, optional
        Correction matrix.  Shaped (2, 12*32).
        first row is 'm', second row 'b'

    Returns
    -------
    spectrum : array
        This will be shaped (len(bin_edges) - 1, 12*32)

    bin_edges : array
        The energy / ADU bin edges (including the right most edge)

    """
    if np.isscalar(bins):
        if corr_mat is not None:
            bin_edges = np.linspace(0, 70, bins+1)
        else:
            bin_edges = np.linspace(0, 4095, bins+1)
    else:
        bin_edges = bins

    # make array to put
    spectrum = np.zeros((len(bin_edges) - 1, 12*32))
    #
    df = pd.DataFrame({k: data[k]
                       for k in ('germ_chip', 'germ_chan', 'germ_pd')})

    for (chip, chan), group in (df.groupby(('germ_chip', 'germ_chan'))):
        gpd = group['germ_pd'].values
        i = int(chip*32+chan)
        if corr_mat is not None:
            gpd *= corr_mat[0, i]
            gpd += corr_mat[1, i]
        spectrum[:, i] = np.histogram(gpd, bins=bin_edges)[0]

    return spectrum, bin_edges


def select_energy_band(spectrum, energy_bins, lo, hi):
    lo_ind, hi_ind = energy_bins.searchsorted([lo, hi])
    return spectrum[lo_ind:hi_ind].sum(axis=0)


def stack_1D_spectrum(spectrum_list, energy_bins, lo, hi):
    return np.array([select_energy_band(s, energy_bins, lo, hi)
                     for s in spectrum_list])


def sum_diffraction(diff_list, detector_angles, angle_bins, *,
                    pixel_scale=0.01741, pixel_offset=0):
    """Align spectra from different angles into 1 curve

    # TODO extend to take np.histogram style binning inputs on angle

    Parameters
    ----------
    diff_list : iterable of 1D data
        Expected shape of elements is (384,)

    detector_angles : iterable
        Must be same length as spectrum_list

    angle_bins : iterable
        The bins to compute the final result in terms of

    pixel_scale : float, optional
        The angular size of a pixel

    pixel_offset : float, optional

    Returns
    -------
    I : array
        The average counts per angle bin

    angle_bins : array
        bin edges (including right most)

    """
    out = np.zeros(len(angle_bins) - 1)
    norm = np.zeros(len(angle_bins) - 1)

    for line, base_angle in zip(diff_list, detector_angles):
        line_angles = (base_angle -
                       (np.arange(384) - 192) * pixel_scale +
                       pixel_offset)

        out += np.histogram(line_angles, weights=line)

    # TODO suppress divide by 0 warnings

    return out / norm, angle_bins
