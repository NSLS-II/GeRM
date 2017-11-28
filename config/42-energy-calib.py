from __future__ import division, print_function
import numpy as np
from lmfit.models import VoigtModel, LinearModel
from scipy.signal import argrelmax
import matplotlib.pyplot as plt


def lamda_from_bragg(th, d, n):
    return 2 * d * np.sin(th / 2.) / n


def find_peaks(chi, sides=6, intensity_threshold=0):
    # Find all potential peaks
    preliminary_peaks = argrelmax(chi, order=20)[0]

    # peaks must have at least sides pixels of data to work with
    preliminary_peaks2 = preliminary_peaks[
        np.where(preliminary_peaks < len(chi) - sides)]

    # make certain that a peak has a drop off which causes the peak height to
    # be more than twice the height at sides pixels away
    criteria = chi[preliminary_peaks2] >= 2 * chi[preliminary_peaks2 + sides]
    criteria *= chi[preliminary_peaks2] >= 2 * chi[preliminary_peaks2 - sides]
    criteria *= chi[preliminary_peaks2] >= intensity_threshold

    peaks = preliminary_peaks[np.where(criteria)]

    left_idxs = peaks - sides
    right_idxs = peaks + sides
    peak_centers = peaks
    left_idxs[left_idxs < 0] = 0
    right_idxs[right_idxs > len(chi)] = len(chi)
    return left_idxs, right_idxs, peak_centers


def get_wavelength_from_std_tth(x, y, d_spacings, ns, plot=False):
    """
    Return the wavelength from a two theta scan of a standard

    Parameters
    ----------
    x: ndarray
        the two theta coordinates
    y: ndarray
        the detector intensity
    d_spacings: ndarray
        the dspacings of the standard
    ns: ndarray
        the multiplicity of the reflection
    plot: bool
        If true plot some of the intermediate data
    Returns
    -------
    float:
        The average wavelength
    float:
        The standard deviation of the wavelength
    """
    l, r, c = find_peaks(y, sides=12)
    n_sym_peaks = len(c)//2
    lmfit_centers = []
    for lidx, ridx, peak_center in zip(l, r, c):
        suby = y[lidx:ridx]
        subx = x[lidx:ridx]
        mod1 = VoigtModel()
        mod2 = LinearModel()
        pars1 = mod1.guess(suby, x=subx)
        pars2 = mod2.make_params(slope=0, intercept=0)
        mod = mod1+mod2
        pars = pars1+pars2
        out = mod.fit(suby, pars, x=subx)
        lmfit_centers.append(out.values['center'])
        if plot:
            plt.plot(subx, out.best_fit, '--')
            plt.plot(subx, suby - out.best_fit, '.')
    lmfit_centers = np.asarray(lmfit_centers)
    if plot:
        plt.plot(x, y, 'b')
        plt.plot(x[c], y[c], 'ro')
        plt.plot(x, np.zeros(x.shape), 'k.')
        plt.show()

    offset = []
    for i in range(0, n_sym_peaks):
        o = (np.abs(lmfit_centers[i]) -  np.abs(lmfit_centers[2*n_sym_peaks-i-1]))/2.
        # print(o)
        offset.append(o)
    print('predicted offset {}'.format(np.median(offset)))
    lmfit_centers += np.median(offset)
    print(lmfit_centers)
    wavelengths = []
    l_peaks = lmfit_centers[lmfit_centers < 0.]
    r_peaks = lmfit_centers[lmfit_centers > 0.]
    for peak_set in [r_peaks, l_peaks[::-1]]:
        for peak_center, d, n in zip(peak_set, d_spacings, ns):
            tth = np.deg2rad(np.abs(peak_center))
            wavelengths.append(lamda_from_bragg(tth, d, n))
    return np.average(wavelengths), np.std(wavelengths), np.median(offset)


from bluesky.callbacks import CollectThenCompute


class ComputeWavelength(CollectThenCompute):
    """
    Example
    -------
    >>> cw = ComputeWavelgnth('tth_cal', 'some_detector', d_spacings, ns) 
    >>> RE(scan(...), cw)
    """
    CONVERSION_FACTOR = 12.3984  # keV-Angstroms
    def __init__(self, x_name, y_name, d_spacings, ns=None):
        self._descriptors = []
        self._events = []
        self.x_name = x_name
        self.y_name = y_name
        self.d_spacings = d_spacings
        self.wavelength = None
        self.wavelength_std = None
        self.offset = None
        if ns is None:
            self.ns = np.ones(self.d_spacings.shape)
        else:
            self.ns = ns

    @property
    def energy(self):
        if self.wavelength is None:
            return None
        else:
            return self.CONVERSION_FACTOR / self.wavelength

    def compute(self):
        x = []
        y = []
        for event in self._events:
            x.append(event['data'][self.x_name])
            y.append(event['data'][self.y_name])

        x = np.array(x)
        y = np.array(y)
        self.wavelength, self.wavelength_std, self.offset = get_wavelength_from_std_tth(x, y, self.d_spacings, self.ns)
        print('wavelength', self.wavelength, '+-', self.wavelength_std)
        print('energy', self.energy)
    
"""
if __name__ == '__main__':
    import os

    # step 0 load data
    calibration_file = os.path.join('../../data/LaB6_d.txt')
    d_spacings = np.loadtxt(calibration_file)
    
    for data_file in ['../../data/Lab6_67p8.chi', '../../data/Lab6_67p6.chi']:
        a = np.loadtxt(data_file)
        wavechange = []
        x = a[:, 0]
        #x = np.hstack((np.zeros(1), x))
        x = np.hstack((-x[::-1], x))
        y = a[:, 1]
        #y = np.hstack((np.zeros(1), y))
        y = np.hstack((y[::-1], y))
        b = np.linspace(0, 3, 100)
        for dx in b:
            print('added offset {}'.format(dx))
            off_x = x[:] + dx
            rv1, rv2, rv3 = get_wavelength_from_std_tth(off_x, y, d_spacings,
                    np.ones(d_spacings.shape), 
#plot=True
                    )
            print(rv1, rv2, rv3)
            print()
            wavechange.append(rv1)
            #input()
        plt.plot(b, wavechange/np.mean(wavechange))
    plt.show()
"""
