import os
from ophyd import Device, Component as Cpt, EpicsSignal, EpicsSignalRO

os.environ['EPICS_CA_ADDR_LIST'] = 'localhost'


class GeRM(Device):
    acquire = Cpt(EpicsSignal, ':acquire')
    filepath = Cpt(EpicsSignal, ':filepath', string=True)
    last_file = Cpt(EpicsSignalRO, ':last_file', string=True)
    uid_chip = Cpt(EpicsSignalRO, ':UUID:CHIP', string=True)
    uid_chan = Cpt(EpicsSignalRO, ':UUID:CHAN', string=True)
    uid_td = Cpt(EpicsSignalRO, ':UUID:TD', string=True)
    uid_pd = Cpt(EpicsSignalRO, ':UUID:PD', string=True)
    uid_ts = Cpt(EpicsSignalRO, ':UUID:TS', string=True)


germ = GeRM('germ', name='germ')
