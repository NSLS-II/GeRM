#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
from __future__ import division
from __future__ import print_function
from builtins import range
from pygerm.zmq import ZClientWriter
from pygerm import TRIGGER_SETUP_SEQ, START_DAQ, STOP_DAQ

import time as tm

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
plt.ion()
from matplotlib.backends.qt_compat import QtWidgets, QtCore


# Create an QApplication object.
a = QtWidgets.QApplication.instance()
if a is None:
    a = QtWidgets.QApplication(["MARS DAQ"])
    a.lastWindowClosed.connect(a.quit)

# The QWidget widget is the base class of all user interface objects in PyQt4.
w = QtWidgets.QWidget()

# Set window size.
w.resize(320, 140)

# Set window title
w.setWindowTitle("MARS DAQ!")

# Add a button
btn_q = QtWidgets.QPushButton('Quit!', w)
btn_trig = QtWidgets.QPushButton('DAQ Trigger', w)


@QtCore.Slot()
def on_trig():
    print('triggered')
    ip_addr = "tcp://localhost"
    zc = ZClientWriter(ip_addr)
    for (addr, val) in TRIGGER_SETUP_SEQ:
        if addr is None:
            tm.sleep(val)
        else:
            zc.write(addr, val)

    print("sent DAQ trigger")
    zc.write(*START_DAQ)
    totallen, bitrate, pd, td, addr = zc.get_data(0)
    print("sent DAQ stop")
    zc.set_trigdaq(*STOP_DAQ)

    read_number = zc.read(0x64)
    print("number of data ", read_number)

    # x1 = np.arange(0, len(td), 1)
    x_len = 50
    x1 = np.arange(0, x_len, 1)
    x = np.arange(0, x_len, 1)

    plt.subplot(3, 2, 1)
    plt.plot(x, [pd[i] for i in range(0, x_len)])
    plt.title('PD')
    plt.grid()

    plt.subplot(3, 2, 2)
    plt.hist(pd, 100, histtype='stepfilled', facecolor='g', alpha=0.75)
    plt.title('PD hist')
    plt.grid()

    plt.subplot(3, 2, 3)
    plt.plot(x1, [td[i] for i in range(0, x_len)])
    plt.title('TD')
    plt.grid()

    plt.subplot(3, 2, 4)
    plt.hist(td, 100, histtype='stepfilled', facecolor='g', alpha=0.75)
    plt.title('TD hist')
    plt.grid()

    plt.subplot(3, 2, 5)
    plt.hist(addr, 32, histtype='stepfilled', facecolor='g', alpha=0.75)
    plt.title('addr hist')
    plt.grid()

    plt.draw()
    plt.show()


btn_q.setToolTip('Click to quit!')
btn_q.clicked.connect(w.close)
btn_trig.clicked.connect(on_trig)
# btn.resize(btn.sizeHint())
btn_q.move(10, 10)
btn_trig.move(150, 10)

# Show window
w.show()

a.exec_()
