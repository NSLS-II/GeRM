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


def fit_all_channels(data, peak_guesses, plot=False):
    '''
        This fits the 2D binned data and fits each column to three peaks.

        This returns the positions of the peaks in the array (not energy
        specific)

        Parameters
        ----------
        data : 2d np.ndarray
            A 2d array of the counts per channel x energy (ADU)

        peak_guesses: 2 lists
            Two lists specifying the window where to expect each peak.

        plot: bool, optional
            Whether or not to plot the data as it is being fit
    '''
    if plot:
        fig, ax = plt.subplots()
    gauss_mod1 = Model(gaussian, prefix='g1_')
    gauss_mod3 = Model(gaussian, prefix='g3_')

    gauss_mod = gauss_mod1+gauss_mod3

    # g2 used to be a peak I removed
    g1_cen_list = []
    g3_cen_list = []
    x = np.arange(data.shape[0])
    for j in range(data.shape[1]):
        print("Fitting peak number {}".format(j))
        g1_cen = peak_guesses[0][0] + \
            np.argmax(data[peak_guesses[0][0]:peak_guesses[0][1], j])
        g3_cen = peak_guesses[1][0] + \
            np.argmax(data[peak_guesses[1][0]:peak_guesses[1][1], j])

        gauss_mod.set_param_hint('g1_center', value=g1_cen, vary=True,
                                 min=g1_cen-30, max=g1_cen+30)
        gauss_mod.set_param_hint('g3_center', value=g3_cen, vary=True,
                                 min=g3_cen-30, max=g3_cen+30)
        gauss_mod.set_param_hint(name='g1_sigma', value=20, vary=True, min=5,
                                 max=40)
        gauss_mod.set_param_hint(name='g3_sigma', value=20, vary=True, min=5,
                                 max=40)

        params = gauss_mod.make_params(g1_center=g1_cen, g1_area=1000,
                                       g1_sigma=10.0, g3_center=g3_cen,
                                       g3_area=1000, g3_sigma=10.0)
        result = gauss_mod.fit(data[:, j], params, x=x)
        g1_cen_list.append(result.values['g1_center'])
        g3_cen_list.append(result.values['g3_center'])
        if plot:
            ax.cla()
            ax.plot(result.data, color='k', label="data")
            ax.plot(result.best_fit, color='r', label="fit")
            ax.legend()
            fig.canvas.draw_idle()
            plt.pause(.00001)

    return g1_cen_list, g3_cen_list
