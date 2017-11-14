from databroker.assets.sqlite import Registry
from databroker.headersource.sqlite import MDS
from databroker import Broker
import bluesky as bs


from pygerm.ophyd import GeRM
from pygerm.handler import GeRMHandler

import numpy as np
import pandas as pd
from lmfit import Model
import os
from pathlib import Path


# generic configuration, is already on the beamline
reg = Registry({'dbpath': '/tmp/fs.sqlite'})
reg.register_handler('GeRM', GeRMHandler)

mds = MDS({'directory': '/tmp/mds.sqlite', 'timezone': 'US/Eastern'})

db = Broker(mds, reg=reg)
RE = bs.RunEngine()
RE.subscribe(db.insert)


# create the GeRM object
germ = GeRM('XF:28IDC-ES:1{Det:GeRM1}', name='germ',
            read_attrs=['filepath', 'last_file',
                        'chip', 'chan',
                        'td', 'pd', 'ts', 'count'],
            configuration_attrs=['frametime'])


# gaussian fit

def gaussian(x, area, center, sigma):
    """standard gaussian function"""
    return area/(np.sqrt(2*np.pi)*sigma)*np.exp(-(x-center)**2/(2*sigma**2))


def linear(x, a, b):
    return a*x+b


def fit_all_channels(data):
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
    return g1_cen_list, g2_cen_list, g3_cen_list


def get_calibration_value(cen_data, y):
    """Linear regression to calculate calibration based on bin center and energy value.

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


# _cal_file = Path(os.path.realpath(__file__)).parent / 'calibration_martix.txt'
# cal_val = np.loadtxt(str(_cal_file))

# How to take a count
# http://nsls-ii.github.io/bluesky/plans_intro.html
# import bluesky.plans as bp
# RE(bp.count([germ]))
