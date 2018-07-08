================
Time Series Data
================

One interesting run is to watch a sample undergo some transformation, such as a
phase transition. Since GeRM provides energy resolved measurements, this can
lead to a 3D data set of (q space, energy, time).

The data is acquired by simply starting the GeRM detector and having it write
ot a binary blob.

It is assumed that you have read the :doc:`calibration <calibration>` step.

The data can be read back in by the following function:

.. code-block: python

    from pygerm.reduction import histogram_germ

    h_vals, h_centers =  histogram_germ(germ_ts, germ_td,
                                        germ_pd, germ_chip, germ_chan,
                                        time_resolution=1, start_time=0,
                                        end_time=240, energy_resolution=30,
                                        min_energy=30, max_energy=60,
                                        calibration=calibration,
                                        td_resolution=40e-9, n_chans=32,
                                        n_chips=12, jump_bits=29, thresh_bits=26,
                                        chunksize=1000000, plot=True)


.. figure:: figs/004_time_series_data.png



