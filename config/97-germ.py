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
# comment these out if running at xpd (since other )
db = Broker.named("xpd")
RE = bs.RunEngine()
RE.subscribe(db.insert)

reg = db.reg

reg.register_handler('GeRM', GeRMHandler)
reg.register_handler('BinaryGeRM', BinaryGeRMHandler)



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
# _cal_file = Path(os.path.realpath(__file__)).parent / 'data/calibration_matrix_20170720.txt'
# this had wrong energies
#_cal_file = Path(os.path.realpath(__file__)).parent / 'data/calibration_matrix_20171129.txt'
# this one calibrated with more precise energies
# _cal_file = Path(os.path.realpath(__file__)).parent / 'data/calibration_matrix_20171129_2.txt'
_cal_file = Path(os.path.realpath(__file__)).parent / 'calibration_matrix_20171129.txt'
_cal_file = Path(os.path.realpath(__file__)).parent / 'data/calibration_matrix_20171130.txt'
cal_val = np.loadtxt(str(_cal_file))

# calibration data uid
# cal_uid = "71b97506-7123-4af3-8d30-c566af324f95"
def run_cal(cal_uid):
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

# Generate calibration matrix:
# cal_val = run_cal('ea6f8286-e9e0-44da-9b30-7f433ea3319b')
# cal_file = '/home/xf28id1/.ipython/profile_collection_germ/startup/data/calibration_matrix_20171130.txt'
# np.savetxt(cal_file, cal_val)

# How to take a count
# http://nsls-ii.github.io/bluesky/plans_intro.html
# import bluesky.plans as bp
# RE(bp.count([germ]))
