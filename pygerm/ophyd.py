import os
from ophyd import Device, Component as Cpt, EpicsSignal, EpicsSignalRO


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
    # go button
    acquire = Cpt(EpicsSignal, ':acquire', put_complete=True)
    # exposure per frame
    frametime = Cpt(EpicsSignal, ':frametime', put_complete=True)
    # data path
    filepath = Cpt(EpicsSignal, ':filepath',
                   string=True, put_complete=True)

    # where the last file was written
    last_file = Cpt(EpicsSignalRO, ':last_file', string=True)
    
    overfill = Cpt(EpicsSignalRO, ':overfill')
    last_frame = Cpt(EpicsSignalRO, ':last_frame')

    # number of events
    count = Cpt(EpicsSignalRO, ':COUNT')
    # fs uuids
    chip = Cpt(GeRMSRO, ':UUID:CHIP', string=True)
    chan = Cpt(GeRMSRO, ':UUID:CHAN', string=True)
    td = Cpt(GeRMSRO, ':UUID:TD', string=True)
    pd = Cpt(GeRMSRO, ':UUID:PD', string=True)
    ts = Cpt(GeRMSRO, ':UUID:TS', string=True)

    def trigger(self):
        return self.acquire.set(1)
