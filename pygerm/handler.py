import h5py
import numpy as np
import dask.array as da

from .client import payload2event, DATA_TYPEMAP


class GeRMHandler():
    specs = {'GeRM'}

    def __init__(self, fpath):
        self._file = h5py.File(fpath, 'r')
        self._g = self._file['GeRM']

    def __call__(self, column):
        return self._g[column][:]

    def close(self):
        self._file.close()


class BinaryGeRMHandler():
    specs = {'BinaryGeRM'}

    def __init__(self, fpath, chunksize=None):
        ''' Binary GeRM handler.

        Parameters
        ----------
        chunksize : int, optional
            if specified, this turns result into a dask array
            This array is a lazy loaded array. To obtain the results
            one must call the .compute() method.
            This is useful when the data is too large to fit in memory.

        Notes
        -----
        When using chunksize, use functools.partial, and functools.wraps
        Example ::
            from functools import partial, wraps
            bgermdask = wraps(BinaryGeRMHandler)(partial(BinaryGeRMHandler,
                                                         chunksize=100000))
            fhandler_init = bgermdask(filename)
            res = fhandler_init['germ_ts']
            # etc...
        '''
        raw_data = np.memmap(fpath, dtype='>u4')

        # verify the data
        first_word = raw_data[0]
        last_word = raw_data[-1]

        if first_word != 0xfeedface:
            msg = "Error, first 32 bit word not 0xfeedface"
            msg += f"\n Got {first_word:#x} instead"
            raise ValueError(msg)

        if last_word != 0xdecafbad:
            msg = "Error, first 32 bit word not 0xdecafbad"
            msg += f"\n Got {last_word:#x} instead"
            raise ValueError(msg)

        # remove first and last region
        raw_data = raw_data[2:-2]

        # now the raw_data is a dask array, lazy loaded
        if chunksize is not None:
            raw_data = da.from_array(raw_data, chunks=chunksize)

        # this will work with lazy or non-lazy modes
        self.data = payload2event(raw_data)

    def __call__(self, column):
        # NOTE: can return a lazy array
        return self.data[DATA_TYPEMAP[column]]

    def close(self):
        self._file.close()
