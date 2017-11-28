from ophyd import EpicsScaler


em = EpicsScaler('XF:28IDC-BI:1{IM:02}', name='em')
em.channels.read_attrs = ['chan%d' % i for i in [22, 21, 20, 23]]
# Default of em.channels.chan22 is 'em_channels_chan22'.
# Change it to 'em_chan22' for brevity.
for ch_name in em.channels.signal_names:
    ch = getattr(em.channels, ch_name)
    ch.name = ch.name.replace('_channels_', '_')

# Energy Calibration Scintillator
sc = EpicsScaler('XF:28IDC-ES:1{Det:SC2}', name='sc')
sc.channels.read_attrs = ['chan%d' % i for i in [1, 2]]
for ch_name in sc.channels.signal_names:
    # Rename sc_channels_chan1 to sc_chan1
    ch = getattr(sc.channels, ch_name)
    ch.name = ch.name.replace('_channels_', '_')
