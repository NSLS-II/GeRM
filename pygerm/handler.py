from filestore import HandlerBase
import h5py
import numpy as np

from .zmq import parsed_event_payload, DATA_TYPEMAP


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
        self.raw_data = np.fromfile(fpath, count=self.dlen, dtype=np.uint64)
        self.data = parsed_event_payload(self.raw_data)

    def __call__(self, column):
        return self.data[DATA_TYPEMAP[column]]

    def close(self):
        self._file.close()

