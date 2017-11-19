from databroker.assets.handlers_base import HandlerBase
import h5py
import numpy as np

from .client import parse_event_payload, DATA_TYPEMAP


class GeRMHandler(HandlerBase):
    specs = {'GeRM'}

    def __init__(self, fpath):
        self._file = h5py.File(fpath, 'r')
        self._g = self._file['GeRM']

    def __call__(self, column):
        return self._g[column][:]

    def close(self):
        self._file.close()


class BinaryGeRMHandler(HandlerBase):
    specs = {'BinaryGeRM'}

    def __init__(self, fpath):
        # TODO : don't save the raw data (here for debugging)
        raw_data = np.fromfile(fpath, dtype='>u8')
        # TODO : when simulated data comes in, verify this is correct
        # endianness and correct for it, don't just raise error
        first_word = raw_data[0] & np.uint64(0xffffffff00000000)
        if first_word != 0xfeedface00000000:
            msg = "Error, first 32 bit word not 0xfeedface"
            msg += f"\n Got {first_word:#x} instead"
            raise ValueError(msg)

        last_word = raw_data[-1] & np.uint64(0xffffffff)
        if last_word != 0xdecafbad:
            msg = "Error, first 32 bit word not 0xdecafbad"
            msg += f"\n Got {last_word:#x} instead"
            raise ValueError(msg)

        # remove first and last region
        raw_data = raw_data[1:-1]
        self.data = parse_event_payload(raw_data)

    def __call__(self, column):
        return self.data[DATA_TYPEMAP[column]]

    def close(self):
        self._file.close()
