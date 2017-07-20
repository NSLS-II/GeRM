from portable_fs.sqlite.fs import FileStore
from portable_mds.sqlite.mds import MDS
from databroker import Broker
import bluesky as bs
import bluesky.plans as bp


from pygerm.ophyd import GeRM
from pygerm.handler import GeRMHandler

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# generic configuration, is already on the beamline
fs = FileStore({'dbpath': '/tmp/fs.sqlite'})
fs.register_handler('GeRM', GeRMHandler)

mds = MDS({'directory': '/tmp/mds.sqlite', 'timezone': 'US/Eastern'})

db = Broker(mds, fs=fs)
RE = bs.RunEngine()
RE.subscribe('all', db.insert)


# create the GeRM object
germ = GeRM('germ', name='germ', read_attrs=['filepath', 'last_file',
                                             'chip', 'chan',
                                             'td', 'pd', 'ts', 'count'])
# gaussian fit
from lmfit import Model
def gaussian(x, area, center, sigma):
    """standard gaussian function"""
    return area/(np.sqrt(2*np.pi)*sigma)*np.exp(-(x-center)**2/(2*sigma**2))

def linear(x, a, b):
    return a*x+b

gauss_mod1 = Model(gaussian, prefix='g1_')
gauss_mod2 = Model(gaussian, prefix='g2_')
gauss_mod3 = Model(gaussian, prefix='g3_')

# add constraints
gauss_mod1.set_param_hint(name='g1_center', value=1000, vary=True, min=800, max=1400)
gauss_mod2.set_param_hint(name='g2_center', value=1100, vary=True, min=800, max=1400)
gauss_mod3.set_param_hint(name='g3_center', value=3500, vary=True, min=3100, max=3900)
gauss_mod2.set_param_hint(name='g2_sigma', value=20, vary=True, min=5, max=30)

gauss_mod = gauss_mod1+gauss_mod2+gauss_mod3

params = gauss_mod.make_params(g1_center=1053, g1_area=1000, g1_sigma=10.0,
                               g2_center=1186, g2_area=1000, g2_sigma=10.0,
                               g3_center=3587, g3_area=1000, g3_sigma=10.0)

def fit_all_channels(data, gauss_mod=gauss_mod):

    g1_cen_list = []
    g2_cen_list = []
    g3_cen_list = []
    x = np.arange(data.shape[0])
    for v in range(data.shape[1]):
        print(v)
        g1_cen = 800+np.argmax(data[800:1400,v])
        g3_cen = 3100+np.argmax(data[3100:3900, v])
        params = gauss_mod.make_params(g1_center=g1_cen, g1_area=1000, g1_sigma=10.0,
                                       g2_center=g1_cen+150, g2_area=1000, g2_sigma=10.0,
                               	       g3_center=g3_cen, g3_area=1000, g3_sigma=10.0)
        result = gauss_mod.fit(data[:,v], params, x=x)
        g1_cen_list.append(result.values['g1_center'])
        g2_cen_list.append(result.values['g2_center'])
        g3_cen_list.append(result.values['g3_center'])
    return g1_cen_list, g2_cen_list, g3_cen_list


def get_calibration_value(cen_data, y):
    """Calculate calibration based on bin center and energy value.
    Parameters
    ----------
    cen_data :
        2D array with shape [number of channels, 3]

    """
    from scipy.stats import linregress
    cal_val = np.zeros(cen_data.shape[0], 2)  # shape is [number of channels, 2]
    for i in range(cen_data.shape[0]):
        out = linregress(cen_data[i,:].T, y)
        cal_val[i, 0] = out[0]
        cal_val[i, 1] = out[1]
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

# How to take a count
# http://nsls-ii.github.io/bluesky/plans_intro.html
# RE(bp.count([germ]))
