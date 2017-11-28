from ophyd import EpicsSignal
from bluesky.suspenders import SuspendBoolHigh

fast_shutter = EpicsSignal('XF:28IDC-ES:1{Sh:Exp}Sw:Cls1-Sts')
shutter_sus = SuspendBoolHigh(fast_shutter, sleep=3)
# RE.install_suspender(shutter_sus)
