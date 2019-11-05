# quick test for Hough transform (to be moved to a routine eventually)
from skimage.filters import threshold_otsu
from skimage.transform import (hough_line, hough_line_peaks,
                               probabilistic_hough_line)

uids = [
"b78361f1-feb6-4856-b339-4693a74ee288",
"b78361f1-feb6-4856-b339-4693a74ee288",
]

hdr = db[uids[0]]

peaks, angles = track_peaks(hdr)


plt.figure(2);
plt.clf()
plt.imshow(peaks, aspect='auto', origin='lower', 
	   extent=[-.5, 383.5, angles[0], angles[-1]])

