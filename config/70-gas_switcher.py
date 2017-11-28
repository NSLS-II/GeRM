from ophyd import EpicsSignalRO, Device
from ophyd import Component as Cpt, DerivedSignal
from bluesky.examples import NullStatus


class GasSignal(DerivedSignal):
    def __init__(self, *args, parent_attr_name, parent, **kwargs):
        signal = getattr(parent, parent_attr_name)
        super().__init__(*args, derived_from=signal, parent=parent, **kwargs)

    def get(self, **kwargs):
        """return the gas name ('Ni')"""
        pos = super().get(**kwargs)
        num_gasses = len(self.parent.gas_list)
        if pos > num_gasses:
            raise ValueError("The gas switcher is at position %d "
                             "but we only know about %d gasses. "
                             "Update gas_list." % (pos, num_gasses))

        return self.parent.gas_list[int(pos - 1)]

    def put(self, gas_name, **kwargs):
        """accept a has name ('Ni') and translate it to a position"""
        pos = 1 + self.parent.gas_list.index(gas_name)
        num_gasses = len(self.parent.gas_list)
        if pos > num_gasses:
            raise ValueError("You have asked to move to position %d "
                             "but we only know about %d gasses. "
                             "Update gas_list first." % (pos, num_gasses))
        return super().put(pos, **kwargs)

    def describe(self):
        res = super().describe()
        k, = res.keys()
        res[k].pop('precision')
        res[k]['dtype'] = 'string'
        return res


class XPDGasSwitcher(Device):
    # The values here are integer, so this tolerance is just made up.
    current_pos = Cpt(EpicsSignal, 'Pos-I',
                      write_pv='Pos-SP', tolerance=0.01 )
    requested_pos = Cpt(EpicsSignal, 'Pos-SP')

    current_gas = Cpt(GasSignal, parent_attr_name='current_pos')
    requested_gas = Cpt(GasSignal, parent_attr_name='requested_pos')

    def __init__(self, *args, gas_list=None, **kwargs):
        if gas_list is None:
            gas_list = []
        self.gas_list = gas_list
        super().__init__(*args, **kwargs)

    def set(self, value):
        """value should be a string like 'Ni'"""
        # This looks confusing, but it's correct and tested.
        if value not in self.gas_list:
            raise KeyError("There is no gas %s in gas_list. "
                           "Update list or use one of these: %r"
                           % (value, self.gas_list))
        return self.current_gas.set(value)

gas = XPDGasSwitcher('XF:28IDC-ES:1{Env:02}', name='gas')
