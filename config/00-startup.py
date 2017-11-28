# Make ophyd listen to pyepics.
from ophyd import setup_ophyd
setup_ophyd()

# Subscribe metadatastore to documents.
# If this is removed, data is not saved to metadatastore.
from bluesky.global_state import gs

from metadatastore.mds import MDS
# from metadataclient.mds import MDS
from databroker import Broker
from databroker.core import register_builtin_handlers
from filestore.fs import FileStore

# pull from /etc/metadatastore/connection.yaml
_mds_config = {'host': 'xf28id-ca1.cs.nsls2.local',
               'database': 'datastore',
               'port': 27017,
               'timezone': 'US/Eastern'}
_fs_config = {'host': 'xf28id-ca1.cs.nsls2.local',
               'database': 'filestore',
               'port': 27017}


mds = MDS(_mds_config, auth=False)
# mds = MDS({'host': CA, 'port': 7770})

# pull configuration from /etc/filestore/connection.yaml
db = Broker(mds, FileStore(_fs_config))
register_builtin_handlers(db.fs)

def ensure_proposal_id(md):
    if 'sample_number' not in md:
        raise ValueError("You forgot the proposal_id.")


gs.RE.subscribe_lossless('all', mds.insert)


# Verify files exist at the end of a run an print confirmation message.
from bluesky.callbacks.broker import verify_files_saved, post_run
gs.RE.subscribe('stop', post_run(verify_files_saved))

# Import matplotlib and put it in interactive mode.
import matplotlib.pyplot as plt
plt.ion()

# Make plots update live while scans run.
from bluesky.utils import install_qt_kicker
install_qt_kicker()

# Optional: set any metadata that rarely changes.
# RE.md['beamline_id'] = 'YOUR_BEAMLINE_HERE'

# convenience imports
from ophyd.commands import *
from bluesky.plans import (count, scan, relative_scan, inner_product_scan,
                           outer_product_scan, adaptive_scan,
                           relative_adaptive_scan)
from bluesky.callbacks import *
from bluesky.spec_api import *
from bluesky.global_state import gs, abort, stop, resume
from time import sleep
import numpy as np

RE = gs.RE  # convenience alias

# RE.md_validator = ensure_proposal_id

# Uncomment the following lines to turn on verbose messages for debugging.
# import logging
# ophyd.logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

gs.RE.md['owner'] = 'xf28id1'
gs.RE.md['group'] = 'XPD'
gs.RE.md['beamline_id'] = 'xpd'

import subprocess
def show_env():
    proc = subprocess.Popen(["conda", "list"], stdout=subprocess.PIPE)
    out, err = proc.communicate()
    a = out.decode('utf-8')
    b = a.split('\n')
    print(b[0].split('/')[-1][:-1])

