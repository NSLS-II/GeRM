#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
from __future__ import division
from __future__ import print_function
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
import zmq

import time as tm

import numpy as np
import matplotlib.pyplot as plt

import sys
from matplotlib.backends.qt_compat import QtWidgets, QtCore

import datetime


class zclient(object):

    ZMQ_DATA_PORT = "5556"
    ZMQ_CNTL_PORT = "5555"
    TOPIC_DATA = b"data"
    TOPIC_META = b"meta"

    def __init__(self, connect_str):
        self.__context = zmq.Context()
        self.data_sock = self.__context.socket(zmq.SUB)
        self.ctrl_sock = self.__context.socket(zmq.REQ)

        self.data_sock.connect(connect_str + ":" + zclient.ZMQ_DATA_PORT)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_DATA)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, zclient.TOPIC_META)

        self.ctrl_sock.connect(connect_str + ":" + zclient.ZMQ_CNTL_PORT)

    def __cntrl_recv(self):
        msg = self.ctrl_sock.recv()
        dat = np.frombuffer(msg, dtype=np.uint32)
        return dat

    def __cntrl_send(self, payload):
        self.ctrl_sock.send(np.array(payload, dtype=np.uint32))

    def write(self, addr, value):
        self.__cntrl_send([0x1, int(addr), int(value)])
        self.__cntrl_recv()

    def read(self, addr):
        self.__cntrl_send([0x0, int(addr), 0x0])
        return int(self.__cntrl_recv()[2])

    def set_trigdaq(self, value):
        self.write(0x00, value)
        # print("Trigger DAQ")

    def get_data(self, chkdata):
        self.nbr = 0
        totallen = 0
        pd = []
        td = []
        addr = []
        start = datetime.datetime.now()

        fd = open('data_4.bin', 'wb')
        print("In Get Data")
        while True:
            [address, msg] = self.data_sock.recv_multipart()

            if msg == b'END':
                print("Received %s messages" % str(self.nbr))
                print("Message END received")
                break
            if (address == zclient.TOPIC_META):
                print("Meta data received")
                meta_data = np.frombuffer(msg, dtype=np.uint32)
                print(meta_data)
                np.savetxt("meta.txt", meta_data, fmt="%x")
            if (address == zclient.TOPIC_DATA):
                print("Event data received")
                data = np.frombuffer(msg, dtype=np.uint16)
                fd.write(data)
                totallen = totallen + len(data)
                print("Msg Num: %d, Msg len: %d, Tot len: %d" % (
                    self.nbr, len(data), totallen))

                for i in range(1, len(data), 8):
                   pd.append(data[i])

                for i in range(0, len(data), 8):
                   td.append(data[i])

                for i in range(6, len(data), 8):
                   addr.append((data[i]) & 255)

                if self.nbr > 5000:
                    break
                self.nbr += 1

        stop = datetime.datetime.now()

        fd.close()
        elapsed = stop - start
        sec = elapsed.seconds + elapsed.microseconds*1.0e-6
        print("Processing time:", elapsed, sec)

        print("Total Size: %d (%d bytes)" % (totallen, totallen * 4))
        bitrate = (old_div(float(totallen*4), float(sec)))
        print('Received %d frames at %f MBps' % (self.nbr, bitrate))

        return totallen, bitrate, pd, td, addr


# Create an PyQT4 application object.
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
    ip_addr = "tcp://10.0.143.100"
    zc = zclient(ip_addr)
    zc.write(0, 64)
    print("reset FPGA state machines")
    zc.write(0, 0)
    zc.write(16, 1)
    print("ADC reads = 2")
    zc.write(24, 2)
    print("reset fifo")
    zc.write(104, 4)
    tm.sleep(0.01)
    zc.write(104, 0)
    tm.sleep(0.01)
    zc.write(104, 1)
    print("sent DAQ trigger")
    zc.set_trigdaq(1)
    totallen, bitrate, pd, td, addr = zc.get_data(0)
    print("sent DAQ stop")
    zc.set_trigdaq(0)
    read_number = zc.read(100)
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

    plt.show()


# btn.setToolTip('Click to quit!')
btn_q.clicked.connect(exit)
btn_trig.clicked.connect(on_trig)
# btn.resize(btn.sizeHint())
btn_q.move(10, 10)
btn_trig.move(150, 10)

# Show window
w.show()

sys.exit(a.exec_())
