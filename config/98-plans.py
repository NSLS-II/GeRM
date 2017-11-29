from tqdm import tqdm


def run_germ(exposure=None, N=2):
    ''' run count scans

        exposure : exposure time in secs
            if not set, use previously set exposure
        N : number of measurements
    '''
    # set frame time to 30 min
    if exposure is not None:
        germ.frametime.put(exposure)
    for i in tqdm(range(N)):
        yield from bp.count([germ])

