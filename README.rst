support for GeRM
================

This includes

- ØMQ server to run on the zinc board to expose the FPGA registers
  and publish the measured data :file:`src/germ_zserver1.c`
- ØMQ consumer in python :file:`pygerm/zmq.py`
- a python IOC for exposing the GeRM to epics (:file:`pygerm/caproto.py`
  and :file:`cli/germ_ioc.py`).  This IOC writes the measured data to
  hdf5 files and inserts documents in to a ``FileStore`` instance.
- Classes for exposing the IOC to ophyd/bluesky (:file:`pygerm/ophyd.py`)
- Handler for reading the files written by the IOC back through
  ``DataBroker`` (:file:`pygerm/handler.py`)
- A simulated detector for testing (:file:`cli/det_sim.py`)
- An example configuration file (:file:`config/97-germ.py`)
- Qt GUI to test triggering the detector (:file:`MARS_DAQ_qt.py`)
- Qt GUI for ASIC configuration (:file:`AJK_parametertree.py`)


Testing
-------

To test this locally (with out access to a real detector), first start
the detector simulation

.. code-block:: bash

  python cli/det_sim.py

Then the IOC

.. code-block:: bash

  python cli/germ_ioc.py localhost

If starting the IOC against the real device use

.. code-block:: bash

  python cli/germ_ioc.py 10.60.0.160


To test the python side, first fire up ``IPython``

.. code-block:: bash

  ipython

and then run the example configuration::

  %run -i config/97-germ.py


You should then have ``RE`` (the ``RunEngine``), ``db`` (a
``DataBroker`` instance), and ``germ`` (the GeRM device) in your local
namespace.


To run a simple count ::

  RE(bp.count([germ]))

and get the header for than run back::

  h = db[-1]

To plot a energy bin by channel heat-map::

  img = make_mars_heatmap(h, np.linspace(0, 4000, 4000))
  fig, ax = plt.subplots()
  ax.imshow(img, aspect='auto')

or a counts per channel histogram::

  channel_counts = make_mars_line(h):
  fig, ax = plt.subplots()
  plt.plot(channel_counts)


Running
-------

.. code-block:: bash
		
   source activate germ_ioc
   python cli/germ_ioc_udp.py 10.28.0.48 10.28.0.210
		

may need to resart if handshaking with collector gets out of sync

User interface
--------------

Editor

.. code-block:: bash

   PYQTDESIGNERPATH=/home/xf28id1/src/pydm:$PYQTDESIGNERPATH designer

.. code-block:: bash

   pydm germdm/main.ui
