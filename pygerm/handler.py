from filestore import HandlerBase
import h5py


class GeRMHandler(HandlerBase):
    specs = {'GeRM'}

    def __init__(self, fpath):
        self._file = h5py.File(fpath, 'r')
        self._g = self._file['GeRM']

    def __call__(self, column):
        return self._g[column][:]

    def close(self):
        self._file.close()
