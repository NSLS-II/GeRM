# how to create the conda analysis environment for the xpd analysis
conda create -n germ_ioc python=3.6 matplotlib scikit-image numpy
source activate germ_ioc

pip install cython ipython ipywidgets pyolog
pip install pymongo lmfit h5py
pip install pyfai

pip install git+http://www.github.com/nsls-ii/databroker
pip install git+http://www.github.com/nsls-ii/bluesky
pip install git+http://www.github.com/nsls-ii/ophyd
pip install git+http://www.github.com/nsls-ii/databroker-browser
pip install git+http://www.github.com/xpdacq/xpdacq
pip install git+http://www.github.com/xpdacq/xpdan
pip install git+http://www.github.com/xpdacq/xpdview
pip install git+http://www.github.com/scikit-beam/scikit-beam
pip install git+http://www.github.com/nsls-ii/germ

conda install readline=6.2.5 --no-deps
