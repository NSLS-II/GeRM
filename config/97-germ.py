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
            print(chip, chan, ct)
            line[chip*32 + chan] += ct
    return line


def make_mars_heatmap(h, bins):
    '''Make a spectrum khymography

    '''
    line = np.zeros((len(bins)-1, 12*32))
    for ev in db.get_events(h, fill=True):
        df = pd.DataFrame(ev['data'])
        for (chip, chan), group in (df[['germ_chip', 'germ_chan', 'germ_pd']]
                                    .groupby(('germ_chip', 'germ_chan'))):
            gpd = group['germ_pd'].values
            line[:, int(chip*32 + chan)] += np.histogram(gpd, bins)[0]

    return line

# How to take a count
# http://nsls-ii.github.io/bluesky/plans_intro.html
# RE(bp.count([germ]))
