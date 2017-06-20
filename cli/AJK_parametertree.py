# -*- coding: utf-8 -*-
"""
This example demonstrates the use of pyqtgraph's parametertree system. This provides
a simple way to generate user interfaces that control sets of parameters. The example
demonstrates a variety of different parameter types (int, float, list, etc.)
as well as some customized parameter types

"""
from __future__ import division
from __future__ import print_function


#import initExample ## Add path to library (just for examples; you do not need this)
from builtins import str
from builtins import range
from past.utils import old_div
from builtins import object
import time as tm

import numpy as np

import zmq


import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


app = QtGui.QApplication([])
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType

fd = open('MARS_param.bin','wb')

class zclient(object):

    ZMQ_DATA_PORT = "5556"
    ZMQ_CNTL_PORT = "5555"
    TOPIC_DATA = "data"
    TOPIC_META = "meta"

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


## test subclassing parameters
## This parameter automatically generates two child parameters which are always reciprocals of each other
class ComplexParameter(pTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'bool'
        opts['value'] = True
        pTypes.GroupParameter.__init__(self, **opts)

        self.addChild({'name': 'A = 1/B', 'type': 'float', 'value': 7, 'suffix': 'Hz', 'siPrefix': True})
        self.addChild({'name': 'B = 1/A', 'type': 'float', 'value': 1/7., 'suffix': 's', 'siPrefix': True})
        self.a = self.param('A = 1/B')
        self.b = self.param('B = 1/A')
        self.a.sigValueChanged.connect(self.aChanged)
        self.b.sigValueChanged.connect(self.bChanged)

    def aChanged(self):
        self.b.setValue(1.0 / self.a.value(), blockSignal=self.bChanged)

    def bChanged(self):
        self.a.setValue(1.0 / self.b.value(), blockSignal=self.aChanged)


## test add/remove
## this group includes a menu allowing the user to add new parameters into its child list
class ScalableGroup(pTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'group'
        opts['addText'] = "Add"
        opts['addList'] = ['str', 'float', 'int']
        pTypes.GroupParameter.__init__(self, **opts)

    def addNew(self, typ):
        val = {
            'str': '',
            'float': 0.0,
            'int': 0
        }[typ]
        self.addChild(dict(name="ScalableParam %d" % (len(self.childs)+1), type=typ, value=val, removable=True, renamable=True))




params = [
    {'name': 'Channel parameters','expanded': False, 'type': 'group', 'children': [
        {'name': 'Ch0','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False, 'tip':"1- enable test capacitor"},
            {'name': 'SM', 'type': 'bool', 'value': True, 'tip':"1- front end shutdown"},
            {'name': 'SEL', 'type': 'bool', 'value': True, 'tip':"1- shaper out on mon 0- leakage on mon"},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch1','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip' : "Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch2','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch3','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch4','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch5','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch6','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip' : "Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch7','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch8','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch9','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch10','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch11','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip' : "Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch12','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch13','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch14','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch15','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch16','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip' : "Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch17','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch18','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch19','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch20','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch21','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip' : "Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch22','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch23','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch24','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch25','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch26','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip' : "Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch27','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch28','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch29','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
         {'name': 'Ch30','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
        {'name': 'Ch31','expanded': False, 'type': 'group', 'children': [
            {'name': 'ST', 'type': 'bool', 'value': False},
            {'name': 'SM', 'type': 'bool', 'value': True},
            {'name': 'SEL', 'type': 'bool', 'value': True},
            {'name': 'DA0:DA2', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip' : "Threshold trim DAC"},
            {'name': 'DP0:DP3', 'type': 'list', 'values': list(range(0,15)), 'value': 0, 'tip':"Pile-up rejection DAC"},
        ]},
     ]},
        {'name': 'Save/Restore functionality', 'type': 'group', 'children': [
        {'name': 'Save State', 'type': 'action'},
        {'name': 'Restore State','expanded': False, 'type': 'action', 'children': [
            {'name': 'Add missing items', 'type': 'bool', 'value': True},
            {'name': 'Remove extra items', 'type': 'bool', 'value': True},
            ]},
        ]},

    #ComplexParameter(name='Custom parameter group (reciprocal values)'),
    #ScalableGroup(name="Expandable Parameter Group", children=[
     #   {'name': 'ScalableParam 1', 'type': 'str', 'value': "default param 1"},
     #   {'name': 'ScalableParam 2', 'type': 'str', 'value': "default param 2"},
    #]),
]

params_2 = [
    {'name': 'Global parameters','expanded': False, 'type': 'group', 'children': [
        {'name': 'TM', 'type': 'bool', 'value': False, 'tip': "0- TOA, 1- TOT"},
        {'name': 'SBM', 'type': 'bool', 'value': True, 'tip': "0- bypass, 1- enable output monitor"},
        {'name': 'SAUX', 'type': 'bool', 'value': True, 'tip': "0- tristate, 1- AUX out monitor"},
        {'name': 'SP', 'type': 'bool', 'value': True, 'tip': "0- neg charge, 1- pos charge"},
        {'name': 'SLH', 'type': 'bool', 'value': True, 'tip': "0- leakage current set by SL, 1- leakage current X 4"},
        {'name': 'Gain', 'type': 'list', 'values': [0,1,2,3], 'value': 2, 'tip':"0-600mv/fc,1-1200,2-1800,3-3600"},
        {'name': 'C0:C4', 'type': 'list', 'values': list(range(0, 31)), 'value': 21, 'tip':"M0=1-Channel monitor M0=0 other monitor"},
        {'name': 'SS0:SS1', 'type': 'list', 'values': [0,1,2,3], 'value': 0, 'tip':"Multi fire suppression tiem 0-250nsec 1-1usec 2-500nsec 3-2usec"},
        {'name': 'TR0:TR1', 'type': 'list', 'values': [0,1,2,3], 'value': 1, 'tip':"RT 0/1: 0-1/3usec 1-2/6usec 2-3/9usec 3- 4/12usec"},
        {'name': 'SSE', 'type': 'bool', 'value': False, 'tip': "1- Enable multiple fire rejection"},
        {'name': 'SPUR', 'type': 'bool', 'value': False, 'tip': "1- pileup rejection enabled"},
        {'name': 'RT', 'type': 'bool', 'value': False, 'tip':"1- Ramp time X3"},
        {'name': 'T0:T1', 'type': 'list', 'values': [0,1,2,3], 'value': 2, 'tip':"Shaping Time 0-0.25usec,1-1usec,2-0.5usec,3-2usec"},
        {'name': 'SL', 'type': 'bool', 'value': False, 'tip': "1- disable internal leakage current"},
        {'name': 'SB', 'type': 'bool', 'value': True, 'tip': "1- enable buffer for PD"},
        {'name': 'SBN', 'type': 'bool', 'value': True, 'tip': "1- enable neg buffer for PD"},
        {'name': 'M1', 'type': 'bool', 'value': False, 'tip': "0- peak det on PD 1- other mon on PD"},
        {'name': 'M0', 'type': 'bool', 'value': True, 'tip': "1- chan monitor 0- other monitor"},
        {'name': 'SENF2', 'type': 'bool', 'value': True, 'tip': "1- Aquisition stop on threshold"},
        {'name': 'SENF1', 'type': 'bool', 'value': False, 'tip': "1- Aquisition stop on peak"},
        {'name': 'RM', 'type': 'bool', 'value': True, 'tip': "Readout 0- async.  1- sync."},
        #{'name': 'PB0:PB9', 'type': 'list', 'values': range(0, 1024), 'value': 102, 'tip':"Test Pulser"},
        {'name': 'PB0:PB9', 'type': 'int', 'limits': (0, 1023), 'value': 102, 'tip':"Test Pulser"},
        {'name': 'PA0:PA9', 'type': 'int', 'limits': (0, 1023), 'value': 380, 'tip':"Threshold"},
                ]},
     {'name': 'Load MARS', 'type': 'group', 'children': [
     {'name': 'Global reset', 'type': 'action'},
     {'name': 'Load State', 'type': 'action' , 'children':[
        {'name': 'MARS address', 'type': 'list', 'values': [0,1,2,3,4,5,6,7,8,9,10,11,12], 'value': 1, 'tip' : "ASIC to load"}
     ]},
      ]},
    {'name': 'Global actons', 'type': 'group','expanded': False, 'children': [
    {'name': 'Set actions', 'type': 'action' , 'children':[
        {'name': 'MARS clocking', 'type': 'list', 'values': [0,2,4,8], 'value': 2, 'tip' : "0- 80Mhz, 2- 40Mhz, 4- 20MHz, 8- 10Mhz"},
        {'name': 'Test pulser', 'type': 'bool', 'value': True, 'tip': "1- pulser enabled"},
        {'name': 'MARS 1 disable', 'type': 'bool', 'value': False, 'tip': "1- disabled"},
        {'name': 'MARS 2 disable', 'type': 'bool', 'value': False, 'tip': "1- disabled"},
        {'name': 'MARS 3 disable', 'type': 'bool', 'value': False, 'tip': "1- disabled"},
        {'name': 'MARS DAQ delays', 'type': 'int', 'limits': (0, 65534), 'value': 15,'tip' : "0- 80Mhz, 2- 40Mhz, 4- 20MHz, 8- 10Mhz"},
     ]},
     ]},
    ]
## Create tree of Parameter objects
p = Parameter.create(name='params', type='group', children=params)
p2 = Parameter.create(name='params_2', type='group', children=params_2)

ip_addr = "tcp://10.0.143.160"
zc = zclient(ip_addr)


## If anything changes in the tree, print a message
def change(param, changes):
    print("tree changes:")
    for param, change, data in changes:
        path = p.childPath(param)
        if path is not None:
            childName = '.'.join(path)
        else:
            childName = param.name()
        print('  parameter: %s'% childName)
        print('  change:    %s'% change)
        print('  data:      %s'% str(data))
        print('  ----------')

p.sigTreeStateChanged.connect(change)

def change_2(param_2, changes):
    print("tree changes:")
    for param_2, change, data in changes:
        path = p2.childPath(param_2)
        if path is not None:
            childName = '.'.join(path)
        else:
            childName = param_2.name()
        print('  parameter: %s'% childName)
        print('  change:    %s'% change)
        print('  data:      %s'% str(data))
        print('  ----------')

p2.sigTreeStateChanged.connect(change_2)


def valueChanging(param, value):
    print(("Value changing (not finalized):", param, value))

def valueChanging_2(param_2, value):
    print(("Value changing (not finalized):", param_2, value))

# Too lazy for recursion:
for child in p.children():
    child.sigValueChanging.connect(valueChanging)
    for ch2 in child.children():
        ch2.sigValueChanging.connect(valueChanging)

for child in p2.children():
    child.sigValueChanging.connect(valueChanging_2)
    for ch2 in child.children():
        ch2.sigValueChanging.connect(valueChanging_2)



def save():
    global state
    global mars_msw
    global mars_mid13
    global mars_mid

    state = p.saveState()

    tm = int(p2.param('Global parameters','TM').value()) << 31
    sbm = int(p2.param('Global parameters','SBM').value()) << 30
    saux = int(p2.param('Global parameters','SAUX').value()) << 29
    sp = int(p2.param('Global parameters','SP').value()) << 28
    slh = int(p2.param('Global parameters','SLH').value()) << 27
    gn = int(p2.param('Global parameters','Gain').value()) << 25
    c0 = int(p2.param('Global parameters','C0:C4').value()) << 20
    ss = int(p2.param('Global parameters','SS0:SS1').value()) << 18
    tr = int(p2.param('Global parameters','TR0:TR1').value()) << 16
    sse = int(p2.param('Global parameters','SSE').value()) << 15
    spur = int(p2.param('Global parameters','SPUR').value()) << 14
    rt = int(p2.param('Global parameters','RT').value()) << 13
    t0 = int(p2.param('Global parameters','T0:T1').value()) << 11
    sl = int(p2.param('Global parameters','SL').value()) << 10
    sb = int(p2.param('Global parameters','SB').value()) << 9
    sbn = int(p2.param('Global parameters','SBN').value()) << 8
    m1 = int(p2.param('Global parameters','M1').value()) << 7
    m0 = int(p2.param('Global parameters','M0').value()) << 6
    senf2 = int(p2.param('Global parameters','SENF2').value()) << 5
    senf1 = int(p2.param('Global parameters','SENF1').value()) << 4
    rm = int(p2.param('Global parameters','RM').value()) << 3
    pb = int(p2.param('Global parameters','PB0:PB9').value()) >> 7

    mars_msw = (tm | sbm | saux | sp | slh | gn | c0 | ss | tr | sse| spur | rt | t0 | sl | sb | sbn | m1 | m0 | senf2 | senf1 | rm  | pb)

    print("MARS MSW: %X" % mars_msw)

    com= []

    #for i in range(0,32):
     #   chan = "Ch" + str(i)
        #print (chan)
     #   st = int(p.param('Channel parameters', chan, "ST").value()) << 11
     #   sm = int(p.param('Channel parameters', chan, "SM").value()) << 10
     #   sel = int(p.param('Channel parameters', chan, "SEL").value()) << 8
     #   da = int(p.param('Channel parameters', chan,'DA0:DA2').value()) << 5
     #   dp = int(p.param('Channel parameters', chan, "DP0:DP3").value())
     #   com.append(st | sm | sel | da | dp)

    for i in range(0,32):
        chan = "Ch" + str(31 -i)
        com.append(int(p.param('Channel parameters', chan, "ST").value()))
        com.append(int(p.param('Channel parameters', chan, "SM").value()))
        com.append(int(0))
        com.append(int(p.param('Channel parameters', chan, "SEL").value()))
        com.append(int(p.param('Channel parameters', chan,'DA0:DA2').value()) & 4)
        com.append(int(p.param('Channel parameters', chan,'DA0:DA2').value()) & 2)
        com.append(int(p.param('Channel parameters', chan,'DA0:DA2').value()) & 1)
        com.append(int(0))
        com.append(int(p.param('Channel parameters', chan,'DP0:DP3').value()) & 8)
        com.append(int(p.param('Channel parameters', chan,'DP0:DP3').value()) & 4)
        com.append(int(p.param('Channel parameters', chan,'DP0:DP3').value()) & 2)
        com.append(int(p.param('Channel parameters', chan,'DP0:DP3').value()) & 1)

    for w in range(0,15):
        com.append(int(0))


    com.reverse()
    #print (com)

    mars_int =int(0)
    for j in range(0,15):
        mars_int = ((mars_int)<<1 | com.pop())

    #print "mars int : %X" % mars_int

    #mars_mid13 = ((int(p2.param('Global parameters','PB0:PB9').value()) & 127) << 25 | (int(p2.param('Global parameters','PA0:PA9').value())) << 15 | (com[31]) << 3 | (com[30]) >> 9 )
    mars_mid13 = ((int(p2.param('Global parameters','PB0:PB9').value()) & 127) << 25 | (int(p2.param('Global parameters','PA0:PA9').value())) << 15 | mars_int )



    print("MARS Mid 13: %X" % mars_mid13)

    mars_mid = []
    mars_int2 = int(0)
    for n in range(0, 12):
        mars_int2 = int(0)
        for v in range(0,32):
            mars_int2 = ((mars_int2)<<1 | com.pop())
        print("mars int2 : %08X" % mars_int2)
        mars_mid.append(mars_int2)

    #print (mars_mid)



def restore():
    global state
    add = p['Save/Restore functionality', 'Restore State', 'Add missing items']
    rem = p['Save/Restore functionality', 'Restore State', 'Remove extra items']
    p.restoreState(state, addChildren=add, removeChildren=rem)

p.param('Save/Restore functionality', 'Save State').sigActivated.connect(save)
p.param('Save/Restore functionality', 'Restore State').sigActivated.connect(restore)

def load_MARS():
    save()

    print("Load Mars")
    zc.write(0,4)
    zc.write(0,0)

    zc.write(8,mars_msw)
    zc.write(0,2)
    zc.write(0,0)
    tm.sleep(0.01)

    zc.write(8,mars_mid13)
    zc.write(0,2)
    zc.write(0,0)
    tm.sleep(0.01)

    for i in range(0,12):
        zc.write(8,mars_mid[i])
        zc.write(0,2)
        zc.write(0,0)
        tm.sleep(0.01)

    mars_addr = int(p2.param('Load MARS', 'Load State','MARS address').value())

    if (mars_addr == 0):
        zc.write(0,0x00010000)
    elif (mars_addr == 1):
        zc.write(0,0x00020000)
    elif (mars_addr == 2):
        zc.write(0,0x00040000)
    elif (mars_addr == 3):
        zc.write(0,0x00080000)
    elif (mars_addr == 4):
        zc.write(0,0x00100000)
    elif (mars_addr == 5):
        zc.write(0,0x00200000)
    elif (mars_addr == 6):
        zc.write(0,0x00400000)
    elif (mars_addr == 7):
        zc.write(0,0x00800000)
    elif (mars_addr == 8):
        zc.write(0,0x01000000)
    elif (mars_addr == 9):
        zc.write(0,0x02000000)
    elif (mars_addr == 10):
        zc.write(0,0x04000000)
    elif (mars_addr == 11):
        zc.write(0,0x08000000)
    else:
           zc.write(0,0x0FFF0000) #configure all

    zc.write(0,0)

def MARS_reset():
    print("Global Reset")
    zc.write(0,128)
    zc.write(0,0)

def global_set():
    mars_mis = int(0)
    mars_clock = int(p2.param('Global actons', 'Set actions','MARS clocking').value())
    test_pulse = int(p2.param('Global actons', 'Set actions','Test pulser').value())
    mars1_disable = int(p2.param('Global actons', 'Set actions','MARS 1 disable').value()) << 16
    mars2_disable = int(p2.param('Global actons', 'Set actions','MARS 2 disable').value()) << 17
    mars3_disable = int(p2.param('Global actons', 'Set actions','MARS 3 disable').value()) << 18
    mars_delays = int(p2.param('Global actons', 'Set actions','MARS DAQ delays').value())
    mars_mis = mars1_disable | mars2_disable  | mars3_disable | mars_delays
    print("mars clock %04X" % mars_clock)
    zc.write(52,mars_clock)
    print("test pulser %X" % test_pulse)
    zc.write(32,test_pulse)
    print("MARS mis %X" % mars_mis)
    zc.write(56,mars_mis)


p2.param('Global actons', 'Set actions').sigActivated.connect(global_set)
p2.param('Load MARS', 'Load State').sigActivated.connect(load_MARS)
p2.param('Load MARS', 'Global reset').sigActivated.connect(MARS_reset)
## Create two ParameterTree widgets, both accessing the same data
t = ParameterTree()
t.setParameters(p, showTop=False)
t.setWindowTitle('MARS settings')
t2 = ParameterTree()
t2.setParameters(p2, showTop=False)

win = QtGui.QWidget()
layout = QtGui.QGridLayout()
win.setLayout(layout)
layout.addWidget(QtGui.QLabel("  MARS Parameters  "), 0,  0, 1, 2)
layout.addWidget(t, 1, 0, 1, 1)
layout.addWidget(t2, 1, 1, 1, 1)
win.show()
win.resize(800,800)

## test save/restore
s = p.saveState()
p.restoreState(s)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
