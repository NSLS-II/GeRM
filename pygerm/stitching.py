import numpy as np


def stitch(line1, pos1, counts1, line2, pos2, counts2, dpos=1):
    '''
        Stitch images

        Written in a stateless fashion.

        i.e. can be streamed in an accumulator
        See streamz.accumulator (streamz library)

        Parameters
        ----------
        line1: list
            the first data
        pos1: list
            the positions
        counts1: list
            the counts in each pixel (can be fractional)

        line2: list
            the second data to interpolate with
        pos2: list
            the positions
        counts2: list
            the counts in each pixel (can be fractional)

        dres : min res
    '''
    # first compute the range
    min_range = min(np.min(pos1), np.min(pos2))
    max_range = max(np.max(pos1), np.max(pos2))
    nsteps = int(max_range-min_range)/dpos

    new_range = np.linspace(min_range, max_range, nsteps)

    # now interp the line and counts for the first line
    # (interping the counts is a trick to get the weights right)
    w1 = np.where((new_range > pos1[0])*(new_range < pos1[-1]))
    line1_new = np.interp(new_range[w1], pos1, line1)
    counts1_new = np.interp(new_range[w1], pos1, counts1)

    # now interp the line and counts for the second line
    w2 = np.where((new_range > pos2[0])*(new_range < pos2[-1]))
    line2_new = np.interp(new_range[w2], pos2, line2)
    counts2_new = np.interp(new_range[w2], pos2, counts2)

    # now add these results into the original line
    new_line = np.zeros_like(new_range)
    new_counts = np.zeros_like(new_range)
    new_line[w1] += line1_new
    new_counts[w1] += counts1_new
    new_line[w2] += line2_new
    new_counts[w2] += counts2_new

    return new_line, new_range, new_counts
