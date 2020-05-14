=================
Reading GeRM data
=================

To read GeRM data, you need to use a file handler.
Reading is a two step process: instantiation and then access.

Importing The Handler
---------------------

When importing the file handler, you might want to give it some extra options.
Instantiate the file handler like so:

.. code-block:: python

    from functools import partial, wraps
    from pygerm.handler import BinaryGeRMHandler

    BinaryGeRMHandlerDask = \
        wraps(BinaryGeRMHandler)(partial(BinaryGeRMHandler,
                                         chunksize=1000000))
   
Here, ``chunksize`` is an optional argument that lazy loads the data. If
specified, the handler will be using the `dask
<http://www.github.com/dask/dask>`_. library to load the data.  Since GeRM data
is normally quite large, you'll almost always want to do this.  The larger the
chunksize, the quicker the read operations. However, make it too large and
you'll run out of memory. It is recommended that the user play with this
parameter and watch memory usage before beginning.




Connecting with databroker
--------------------------
At NSLS-II, the data is saved in databroker. This obviates the need for
understanding the existing file formats. We can register this handler easily.
For example:

.. code-block:: python

    from functools import partial, wraps
    from databroker import Broker
    db = Broker.named("xpd")

    BinaryGeRMHandlerDask = \
        wraps(BinaryGeRMHandler)(partial(BinaryGeRMHandler,
                                         chunksize=1000000))
    db.reg.register_handler("BinaryGeRM", BinaryGeRMHandlerDask)

The ``functools.partial`` module is crucial to pass a function partially
initialized to a desired chunk size (``databroker`` will know nothing of how to
chunk data).

Currently at NSLS-II, databroker is configured to save each entry as a separate
column in a dataframe. So:

.. code-block:: python

    hdr = db[someuid]
    df = hdr.data(stream_name="primary", fields=["timestamp_coarse",
    "timestamp_fine", "energy", "chip", "chan")

Will give a ``pandas.DataFrame`` with the colums specified here.


For more information on databroker see `here
<https://nsls-ii.github.io/databroker>`_.


Advanced: Reading from a raw file
---------------------------------

Sometimes it might be needed to read from a raw file. Finally, reading from a
file is simple. Just instantiate your handler with the filename:

.. code-block:: python

    han = BinaryGeRMHandlerDask(fpath)

The GeRM data is a binary blob that contains lists of the following:
* **timestamp_coarse** : A coarse time stamp
* **timestamp_fine** : A fine time stamp. This will generally overflow, so
you'll have to watch for that.
* **energy** : The energy measured (in Analog Digital Units, or ADU) 
* **chip** : the chip number. There are a certain number of channels per chip.
* **chan** : the channel number within a chip. As of the time of this writing,
there are 32 channels per chip.

These blobs are easily read as simple ``numpy`` arrays with the following
function calls:

.. code-block:: python

    germ_ts = han('timestamp_coarse').astype(np.uint32)
    germ_td = han('timestamp_fine').astype(np.uint32)
    germ_pd = han('energy').astype(np.uint32)
    germ_chip = han('chip').astype(np.uint32)
    germ_chan = han('chan').astype(np.uint32)

An additional typecasting was added to ensure math operations don't overflow
(for example, for **germ_td** the fine timestamp).

You may name the variables in any way you want, but in general, we follow this
naming convention here:

* **germ_ts** -> **timestamp_coarse**
* **germ_td** -> **timestamp_fine**
* **germ_pd** -> **energy**
* **chip** -> **chip**
* **chan** -> **chan**


.. code-block:: python

    germ_ts = han('timestamp_coarse').astype(np.uint32)
    germ_td = han('timestamp_fine').astype(np.uint32)
    germ_pd = han('energy').astype(np.uint32)
    germ_chip = han('chip').astype(np.uint32)
    germ_chan = han('chan').astype(np.uint32)

