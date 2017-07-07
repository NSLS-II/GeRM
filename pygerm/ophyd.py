import os
from ophyd import Device, Component as Cpt, EpicsSignal, EpicsSignalRO
import numpy as np
import pandas as pd

os.environ['EPICS_CA_ADDR_LIST'] = 'localhost'


class GeRMSRO(EpicsSignalRO):
    def describe(self):
        # TODO patch up describe for count + external
        ret = super().describe()
        desc = ret[self.name]
        desc['shape'] = [self.parent.count.get(), ]
        desc['external'] = 'FILESTORE:'
        desc['dtype'] = 'array'
        return ret


class GeRM(Device):
    acquire = Cpt(EpicsSignal, ':acquire', put_complete=True)
    filepath = Cpt(EpicsSignal, ':filepath', string=True)
    last_file = Cpt(EpicsSignalRO, ':last_file', string=True)

    count = Cpt(EpicsSignalRO, ':COUNT')
    chip = Cpt(GeRMSRO, ':UUID:CHIP', string=True)
    chan = Cpt(GeRMSRO, ':UUID:CHAN', string=True)
    td = Cpt(GeRMSRO, ':UUID:TD', string=True)
    pd = Cpt(GeRMSRO, ':UUID:PD', string=True)
    ts = Cpt(GeRMSRO, ':UUID:TS', string=True)

    def trigger(self):
        return self.acquire.set(1)


