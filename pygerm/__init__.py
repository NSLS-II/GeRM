from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

TRIGGER_SETUP_SEQ = (
    (0x0, 64),
    # reset FPGA state machines
    (0x0, 0),
    (0x10, 1),
    # ADC reads = 2
    (0x18, 2),
    # reset fifo
    (0x68, 4),
    (None, 0.01),
    (0x68, 0),
    (None, 0.01),
    (0x68, 1),
    (0xD0, 1)
)

START_DAQ = (0x0, 1)
STOP_DAQ = (0x0, 0)
