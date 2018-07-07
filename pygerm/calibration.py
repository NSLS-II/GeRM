import numpy as np
import matplotlib.pyplot as plt
from lmfit import Model
from lmfit.lineshapes import gaussian


def run_cal(heat_map,
            energies=[17.4, 59.5],
            peak_guesses=[[800, 1400], [3100, 3900]],
            plot=False):
    ''' Function to run on calibration.

        The heat_map is a 2d matrix of channel x energy of counts measured from
        the GeRM detector. This must contain data with two obvious peaks at
        known energies. The energies are supplied using energies and the peak
        windows are supplied with peak guesses. Note : this is a very simple
        fitting routine. It just looks for the max value in two windows. To
        keep things simple, the user should do their best to supply a
        reasonable guess for the peak windows through peak_guesses.

        Parameters
        ----------

        heat_map: 2d np.ndarray
            A 2d array of the counts per channel x energy (ADU)

        energies: list of floats
            energies of the calibration in keV

        plot: bool, optional
            Whether or not to plot this data as it is fit.
            Default is False.

        Returns
        -------
        cal_mat : 2d np.ndarray
            2d array of the calibration values
    '''
    cens = fit_all_channels(heat_map, peak_guesses=peak_guesses, plot=plot)
    # change to numpy array for function
    cens = np.array(cens)
    cal_mat = get_calibration_value(cens, energies)
    return cal_mat


def get_calibration_value(cen_data, y):
    """Linear regression to calculate calibration

        Based on bin center and energy value.
        Assumes data comes from the fit run on mars_heatmap code for three
        peaks.

        The three peaks should be the molydenum k-alpha, kbeta and Americium
        peak (at 60keV or so).
        The americium emits at 60keV and excites the molybdenum, which then
        emits at the k-alpha and k-beta lines.

        Energies:
            americium : 59.5 keV
            Mo K-alpha : 17.4 keV (not used)
            Mo K-beta : 19.6 keV

    Parameters
    ----------
    cen_data :
        2D array with shape [number of data, number of x]


    Output
    ------
    2d array:
        shape [2, number of data], First data is slope and
        the second is intercept.
    """
    from scipy.stats import linregress
    # shape is [number of channels, 2]
    cal_val = np.zeros([2, cen_data.shape[1]])
    for i in range(cen_data.shape[1]):
        out = linregress(cen_data[:, i], y)
        cal_val[0, i] = out[0]
        cal_val[1, i] = out[1]
    return cal_val


def fit_all_channels(data, peak_guesses, peak_sigmas=None, plot=False):
    '''
        This fits the 2D binned data and fits each column to three peaks.

        This returns the positions of the peaks in the array (not energy
        specific)

        Parameters
        ----------
        data : 2d np.ndarray
            A 2d array of the counts per channel x energy (ADU)

        peak_guesses: N lists
            N lists specifying the window where to expect each peak.

        peak_sigmas: N lists
            N lists specifying the window of sigmas for the peaks

        plot: bool, optional
            Whether or not to plot the data as it is being fit
    '''
    if plot:
        fig, ax = plt.subplots()

    Npeaks = len(peak_guesses)
    if peak_sigmas is None:
        peak_sigmas = [[4, 50] for i in range(Npeaks)]

    def background(x, constant=0):
        return constant

    model = Model(background, prefix="bg_")
    for i in range(Npeaks):
        model = model + Model(gaussian, prefix=f'g{i}_')

    cen_list =  [[] for i in range(Npeaks)]

    x = np.arange(data.shape[0])

    for j in range(data.shape[1]):
        print("Fitting peak number {}".format(j))
        param_kwargs = {}
        #param_kwargs['bg_constant'] = np.min(data[:,j])
        bg_est = np.min(data[:,j])
        model.set_param_hint('bg_constant', value=bg_est, vary=True)
        for i, peak_guess in enumerate(peak_guesses):
            cen = peak_guess[0] + \
                np.argmax(data[peak_guess[0]:peak_guess[1], j])
            amp = data[cen,j]
            model.set_param_hint(f'g{i}_amplitude', value=amp, vary=True,
                                     min=0, max=np.inf)
            model.set_param_hint(f'g{i}_center', value=cen, vary=True,
                                     min=cen-30, max=cen+30)
            model.set_param_hint(name=f'g{i}_sigma', value=10, vary=True,
                                     min=peak_sigmas[i][0],
                                     max=peak_sigmas[i][1])
            #param_kwargs[f'g{i}_amplitude'] = amp
            #param_kwargs[f'g{i}_center'] = cen
            #param_kwargs[f'g{i}_sigma'] = 10.

        params = model.make_params()

        result = model.fit(data[:, j], params, x=x)

        for i in range(Npeaks):
            cen_list[i].append(result.values[f'g{i}_center'])

        if plot:
            ax.cla()
            ax.plot(result.data, color='k', label="data")
            ax.plot(result.best_fit, color='r', label="fit")
            ax.legend()
            fig.canvas.draw_idle()
            plt.pause(.00001)

    return cen_list


def compute_corrs(h_lines):
    '''
        Compute the correlations for the data along an axis.

        Parameters
        ----------
        data: 2d np.ndarray
            a set of lines of Nlines x Nsteps
            where Nsteps are arbitrary dimension

        See Also
        --------
        skbeam.core.correlation.CrossCorrelator
    '''
    corrs = np.fft.ifft(np.fft.fft(h_lines[:-1],axis=1)*
                        np.conj(np.fft.fft(h_lines[1:], axis=1))).real
    return corrs


def compute_shifts(data,plot=False):
    '''
        Calculate the shift per step, for list of lines.

        Usually, step is in tth and we measure how many pixels
            a measurement has moved by.

        Parameters
        ----------

        data : 2d np.ndarray
            the data, lines versus channels
            we measure the shift from one line to the other

        plot: bool, optional
            Whether or not to plot the data

        Notes
        -----
        For this to succeed, it's usually best to make sure the shift of the
        data is not more than a few pixels in steps.

        Returns
        -------

        shifts : list
            list of the shifts computed for each step
    '''
    corrs = compute_corrs(data.astype(float))
    step_diffs = fit_all_channels(corrs.T, peak_guesses=[[0,200]],
                                  peak_sigmas=[[0.1, 3]], plot=plot)[0]
    return step_diffs


def compute_tth_per_step(h_lines, tths, plot=False):
    '''
        Compute the tth change per step for a set of line measurements.

        Parameters
        ----------
        h_lines : 2d np.ndarray
            the lines that shift in dimensions of Nlines x Ntthetas

        tths: 1d np.ndarray
            The shift in tth per line

        plot : bool, optional
            whether or not to plot the intermediate result
    '''

    step_diffs = compute_shifts(h_lines, plot=plot)
    tth_diffs = np.abs(np.diff(tths))
    tth_per_step = np.mean(tth_diffs/step_diffs)
    tth_per_step_std = np.std(tth_diffs/step_diffs)

    return tth_per_step, tth_per_step_std
