# some setup
def open_file(fpath):
    return h5py.File(fpath, 'r')


def hdf52event(fpath):
    ''' requires fpath'''
    # hdf5 file
    f = open_file(fpath)

    h = f["GeRM"]

    elem_dict = dict()
    for key in list(DATA_TYPEMAP):
        elem_dict[key] = np.array(h[key], dtype=np.uint64)

    return elem_dict

def hdf52germ(fpath):
    res = hdf52event(fpath)
    # TODO : make this more formal
    new_dict = dict()
    new_dict['chip'] = res['chip']
    new_dict['chan'] = res['chan']
    new_dict['td'] = res['timestamp_fine']
    new_dict['pd'] = res['energy']
    new_dict['ts'] = res['timestamp_coarse']
    return payload2germ(**new_dict)
