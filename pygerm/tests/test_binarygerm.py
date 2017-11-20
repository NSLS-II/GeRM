import numpy as np
import tempfile

from pygerm.client import payload2event, event2payload
from pygerm.handler import BinaryGeRMHandler

'''
numpy issue with anding np.uint64 see here:
    https://github.com/numpy/numpy/issues/2955
use np.uint64(0x111) typecasting for every unit wise operation
'''


def generate_payload():
    ''' Generate random payload data from a GeRM detector.

        This generates the contents of the germ packet described in the GeRM
        format documentation for the binary file.

        The full packet is:
        32-bit uint : 0xfeedface
        32-bit uint
        [list of 32-bit uints of GeRM data two words per GeRM data]
        32-bit uint
        32-bit uint : 0xdecafbad

        where the list of 64-bit uints of GeRM data is what this function
        returns.

        NOTE : "Word" is defined here as a 32 bit unsigned int.
            Note that word normally means the pointer size for memory address
            (64bit in 64bit machines instead of 32 for example)
    '''
    # number of elements
    N = 3000

    # generate some random unsigned ints
    def generate_data(N):
        # <u4 little endian unsigned 4 byte int
        return np.random.randint(low=0, high=1000, size=N, dtype='<u4')

    chip = generate_data(N)
    chan = generate_data(N)
    td = generate_data(N)
    pd = generate_data(N)
    ts = generate_data(N)

    payload = event2payload(chip, chan, td, pd, ts)

    return payload


def generate_germ_data():
    payload = generate_payload()

    germ_data = np.zeros(len(payload)+4, dtype='<u4')

    # slicing preserves the data type
    germ_data[2:-2] = payload
    # some 
    germ_data[0] = 0xfeedface
    # frame number
    germ_data[1] = 0
    # events lost to overflow
    germ_data[-2] = 0
    germ_data[-1] = 0xdecafbad

    return germ_data


def test_binary_germ():
    ''' Test the binary format comes out as expected.
    '''
    # make the tempfile
    fpath = tempfile.mktemp()

    germ_data = generate_germ_data()
    germ_data.astype('>i4').tofile(fpath)
    # strip first and last bit of payload
    # (endianness not issue here since this was generated from memory)
    chip, chan, td, ps, ts = payload2event(germ_data[2:-2])

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
