from databroker.assets.sqlite import Registry
from databroker.headersource.sqlite import MDS
from databroker import Broker
import bluesky as bs
import bluesky.plans as bp

from pathlib import Path
import os
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.widgets import SpanSelector
from matplotlib.colors import LogNorm
from pygerm.reduction import *

from pygerm.ophyd import GeRMUDP
from pygerm.handler import GeRMHandler, BinaryGeRMHandler

import numpy as np
import pandas as pd
from lmfit import Model


# generic configuration, is already on the beamline
#reg = Registry({'dbpath': '/tmp/fs.sqlite'})

#mds = MDS({'directory': '/tmp/mds.sqlite', 'timezone': 'US/Eastern'})
#db = Broker(mds, reg=reg)
db = Broker.named("xpd")
reg = db.reg

reg.register_handler('GeRM', GeRMHandler)
reg.register_handler('BinaryGeRM', BinaryGeRMHandler)

RE = bs.RunEngine()
RE.subscribe(db.insert)


# create the GeRM object
germ = GeRMUDP('XF:28IDC-ES:1{Det:GeRM1}', name='germ',
               read_attrs=['last_file',
                           'chip', 'chan',
                           'td', 'pd', 'ts', 'count', 'overfill'],
               configuration_attrs=['frametime', 'write_root',
                                    'read_root', 'filepath'])

#/XF28IDC/XF28ID1/pe1_data/
germ.write_root.put("/tmp")
germ.read_root.put("/XF28IDC/XF28ID1")
germ.src_mount.put("/mnt/tmp")
germ.dest_mount.put("/XF28IDC/XF28ID1")
germ.filepath.put("pe1_data/GeRM")

# gaussian fit

def gaussian(x, area, center, sigma):
    """standard gaussian function"""
    return area/(np.sqrt(2*np.pi)*sigma)*np.exp(-(x-center)**2/(2*sigma**2))


def linear(x, a, b):
    return a*x+b


def fit_all_channels(data, plot=True):
    '''
        This fits the 2D binned data and fits each column to three peaks.
        This returns the positions of the peaks in the array (not energy specific)
    '''
    if plot:
        fig, ax = plt.subplots()
    gauss_mod1 = Model(gaussian, prefix='g1_')
    gauss_mod2 = Model(gaussian, prefix='g2_')
    gauss_mod3 = Model(gaussian, prefix='g3_')

    gauss_mod = gauss_mod1+gauss_mod2+gauss_mod3

    g1_cen_list = []
    g2_cen_list = []
    g3_cen_list = []
    x = np.arange(data.shape[0])
    for v in range(data.shape[1]):
        print(v)
        g1_cen = 800+np.argmax(data[800:1400,v])
        g3_cen = 3100+np.argmax(data[3100:3900, v])
        gauss_mod.set_param_hint('g1_center', value=g1_cen, vary=True, min=g1_cen-30, max=g1_cen+30)
        gauss_mod.set_param_hint(name='g1_sigma', value=20, vary=True, min=5, max=40)
        gauss_mod.set_param_hint(name='g2_sigma', value=20, vary=True, min=5, max=40)
        params = gauss_mod.make_params(g1_center=g1_cen, g1_area=1000, g1_sigma=10.0,
                                       g2_center=g1_cen+150, g2_area=1000, g2_sigma=10.0,
                               	       g3_center=g3_cen, g3_area=1000, g3_sigma=10.0)
        result = gauss_mod.fit(data[:,v], params, x=x)
        g1_cen_list.append(result.values['g1_center'])
        g2_cen_list.append(result.values['g2_center'])
        g3_cen_list.append(result.values['g3_center'])
        if plot:
            ax.cla()
            ax.plot(result.data, color='k', label="data")
            ax.plot(result.best_fit, color='r', label="fit")
            ax.legend()
            fig.canvas.draw_idle()
            plt.pause(.00001)

    return g1_cen_list, g2_cen_list, g3_cen_list


def get_calibration_value(cen_data, y):
    """Linear regression to calculate calibration based on bin center and energy value.
        Assumes data comes from the fit run on mars_heatmap code for three peaks.

        The three peaks should be the molydenum k-alpha, kbeta and Americium
        peak (at 60keV or so).
        The americium emits at 60keV and excites the molybdenum, which then emits
            at the k-alpha and k-beta lines.

        Energies:
            americium : 59.5 keV
            Mo K-alpha : 17.4 keV
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


def make_mars_line(h, thresh=1000):
    '''Turns heard into counts per channel above thresh
    '''
    line = np.zeros(12*32)
    for ev in db.get_events(h, fill=True):

        df = pd.DataFrame(ev['data'])
        for _, (chip, chan, ct) in (
                (df[['germ_chip', 'germ_chan', 'germ_pd']]
                 .groupby(('germ_chip', 'germ_chan'))
                 .apply(lambda g: np.sum(g > thresh))['germ_pd'])
                .reset_index()
                .iterrows()):
            line[chip*32 + chan] += ct
    return line


def make_mars_heatmap(h):
    '''Make a spectrum khymography

    '''
    bins = 4096
    line = np.zeros((bins, 12*32))
    for ev in db.get_events(h, fill=True):
        df = pd.DataFrame(ev['data'])
        for (chip, chan), group in (df[['germ_chip', 'germ_chan', 'germ_pd']]
                                    .groupby(('germ_chip', 'germ_chan'))):
            gpd = group['germ_pd'].values
            line[:, int(chip*32 + chan)] += np.bincount(gpd, minlength=bins)

    return line


def make_mars_heatmap_after_correction(h, corr_mat=None,
                                       minv=0, maxv=70, bin_num=2000):
    '''Make a spectrum khymography

    '''
    if corr_mat is None:
        corr_mat = cal_val
    bin_edges = np.linspace(minv, maxv, bin_num+1, endpoint=True)
    line = np.zeros((bin_num, 12*32))
    for ev in db.get_events(h, fill=True):
        df = pd.DataFrame(ev['data'])
        for (chip, chan), group in (df[['germ_chip', 'germ_chan', 'germ_pd']]
                                    .groupby(('germ_chip', 'germ_chan'))):
            gpd = group['germ_pd'].values
            i = int(chip*32+chan)
            eng_arr = gpd*corr_mat[0, i] + corr_mat[1, i]
            line[:, i] += np.histogram(eng_arr, bins=bin_edges)[0]
            # line[:, i] += np.bincount(gpd, minlength=bins)
    return line, bin_edges

def plot_all_chan_spectrum(h, *, ax=None, **kwargs):
    spectrum, bins = make_mars_heatmap_after_correction(h, **kwargs)
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(13.5, 9.5))
    else:
        fig = ax.figure

    div = make_axes_locatable(ax)
    ax_r = div.append_axes('right', 2, pad=0.1, sharey=ax)
    ax_t = div.append_axes('top', 2, pad=0.1, sharex=ax)

    ax_r.yaxis.tick_right()
    ax_r.yaxis.set_label_position("right")
    ax_t.xaxis.tick_top()
    ax_t.xaxis.set_label_position("top")
    
    im = ax.imshow(spectrum, origin='lower', aspect='auto', extent=(-.5, 383.5,
                                                                    bins[0], bins[-1]),
                   norm=LogNorm())

    e_line, = ax_r.plot(spectrum.sum(axis=1), bins[:-1] + np.diff(bins))
    p_line, = ax_t.plot(spectrum.sum(axis=0))
    label = ax_t.annotate('[0, 70] kEv', (0, 1), (10, -10),
                          xycoords='axes fraction',
                          textcoords='offset pixels',
                          va='top', ha='left')

    
    def update(lo, hi):
        p_data = integrate_to_angles(spectrum, bins, lo, hi)
        p_line.set_ydata(p_data)
        ax_t.relim()
        ax_t.autoscale(axis='y')

        label.set_text(f'[{lo:.1f}, {hi:.1f}] keV') 
        fig.canvas.draw_idle()
    
    span = SpanSelector(ax_r, update, 'vertical', useblit=True,
                        rectprops={'alpha':.5, 'facecolor':'red'},
                        span_stays=True)

    
    ax.set_xlabel('channel [#]')
    ax.set_ylabel('E [keV]')

    ax_t.set_xlabel('channel [#]')
    ax_t.set_ylabel('total counts')
    
    ax_r.set_ylabel('E [keV]')
    ax_r.set_xlabel('total counts')
    ax.set_xlim(-.5, 383.5)
    ax.set_ylim(bins[0], bins[-1])
    ax_r.set_xlim(xmin=0)
    
    return spectrum, bins, {'center': {'ax': ax, 'im': im},
                        'top': {'ax': ax_t, 'p_line': p_line},
                        'right': {'ax': ax_r, 'e_line': e_line, 'span': span}}

def integrate_to_angles(spectrum, bins, lo, hi):
    lo_ind, hi_ind = bins.searchsorted([lo, hi])
    return spectrum[lo_ind:hi_ind].sum(axis=0)

def track_peaks(h, bin_num=3000):

    lines = []
    angles = []
    for ev in db.get_events(h, fill=True):
        df = pd.DataFrame(ev['data'])
        angles.append(ev['data']['diff_tth_i'])
        line = np.zeros((bin_num, 12*32))
        bin_edges = np.linspace(0, 70, bin_num+1, endpoint=True)
        for (chip, chan), group in (df[['germ_chip', 'germ_chan', 'germ_pd']]
                                    .groupby(('germ_chip', 'germ_chan'))):
            gpd = group['germ_pd'].values
            i = int(chip*32+chan)
            eng_arr = gpd*cal_val[0, i] + cal_val[1, i]
            line[:, i] += np.histogram(eng_arr, bins=bin_edges)[0]

        lines.append(integrate_to_angles(line, bin_edges, 50, 54))
        
    return np.array(lines), angles

    

# _cal_file = Path(os.path.realpath(__file__)).parent / 'calibration_matrix_20170720.txt'
_cal_file = Path(os.path.realpath(__file__)).parent / 'calibration_matrix_20171129.txt'
cal_val = np.loadtxt(str(_cal_file))

# calibration data uid
cal_uid = "71b97506-7123-4af3-8d30-c566af324f95"
def run_cal():
    ''' test function to run calibration.
        meant to be a template to work on.

        Example:
            cal_mat = run_cal()
            # plot result (also returns the heat map)
            res = plot_all_chan_spectrum(hdr,corr_mat=cal_mat2)
            # the binned data
            im = res[0]
    '''
    hdr = db[cal_uid]
    im = make_mars_heatmap(hdr)
    cens = fit_all_channels(im, plot=True)
    # change to numpy array for function
    cens = np.array(cens)
    # energies of the peaks in keV
    energies = np.array([17.4, 19.6, 59.5])
    cal_mat2 = get_calibration_value(cens, energies)
    return cal_mat2


# How to take a count
# http://nsls-ii.github.io/bluesky/plans_intro.html
# import bluesky.plans as bp
# RE(bp.count([germ]))
