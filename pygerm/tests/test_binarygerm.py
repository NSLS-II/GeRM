import os
import h5py
import numpy as np
import tempfile

from pygerm.zmq import parse_event_payload, DATA_TYPEMAP
from pygerm.handler import BinaryGeRMHandler

'''
numpy issue with anding np.uint64 see here:
    https://github.com/numpy/numpy/issues/2955
use np.uint64(0x111) typecasting for every unit wise operation
'''



def payload2germ(chip, chan, td, pd, ts):
    '''
        Reverse the mapping of GERM data type.
    '''
    # uses numpy broadcasting
    data = np.zeros(len(chip), dtype=np.uint64)
    data = data | (chip << 27)
    data = data | (chan << 22)
    data = data | (td << 12)
    data = data | pd
    data = data | ts << 32
    return data

# two steps:
'''
    1. generate the internal data
    2. generate the whole packet

    TODO : endianness check!
'''

def generate_germ_data():
    ''' generate random germ data'''
    # number of elements
    N = 3000
    def generate_data(N):
        return np.random.randint(low=0, high=1000, size=N, dtype='uint32')

    chip = generate_data(N)
    chan = generate_data(N)
    td = generate_data(N)
    pd = generate_data(N)
    ts = generate_data(N)
    germ = payload2germ(chip, chan, td, pd, ts)

    return germ

def generate_germ_packet():
    germ_data = generate_germ_data()

    germ_binary = np.zeros(len(germ_data)+2, dtype=np.uint64)

    germ_binary[1:-1] = germ_data
    germ_binary[0] = 0xfeedface00000000
    germ_binary[-1] = 0xdecafbad

    return germ_binary



def test_binary_germ():
    ''' test interchangeability from old hdf5 file format to germ file
    format.'''
    # make the tempfile
    fpath = tempfile.mktemp()

    germ = generate_germ_packet()
    germ.tofile(fpath)
    # strip first and last bit of payload
    # (endianness not issue here since this was generated from memory)
    chip, chan, td, ps, ts = parse_event_payload(germ[1:-1])

    # instantiate the handler
    handler = BinaryGeRMHandler(fpath)

    # access some element
    read_chip = handler('chip')
    read_chan = handler('chan')
    read_td = handler('timestamp_fine')
    read_ps = handler('energy')
    read_ts = handler('timestamp_coarse')

    assert np.allclose(read_chip, chip)
    assert np.allclose(read_chan, chan)
    assert np.allclose(read_td, td)
    assert np.allclose(read_ps, ps)
    assert np.allclose(read_ts, ts)
