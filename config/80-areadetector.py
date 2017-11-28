import time as ttime
from ophyd.areadetector import (PerkinElmerDetector, ImagePlugin,
                                TIFFPlugin, StatsPlugin, HDF5Plugin,
                                ProcessPlugin, ROIPlugin)
from ophyd.device import BlueskyInterface
from ophyd.areadetector.trigger_mixins import SingleTrigger, MultiTrigger
from ophyd.areadetector.filestore_mixins import (FileStoreIterativeWrite,
                                                 FileStoreHDF5IterativeWrite,
                                                 FileStoreTIFFSquashing,
                                                 FileStoreTIFF)
from ophyd import Signal, EpicsSignal, EpicsSignalRO # Tim test
from ophyd import Component as C
from ophyd import StatusBase

# from shutter import sh1

#shctl1 = EpicsSignal('XF:28IDC-ES:1{Det:PE1}cam1:ShutterMode', name='shctl1')
shctl1 = EpicsMotor('XF:28IDC-ES:1{Sh2:Exp-Ax:5}Mtr', name='shctl1')


class XPDShutter(Device):
    cmd = C(EpicsSignal, 'Cmd-Cmd')
    close_sts = C(EpicsSignalRO, 'Sw:Cls1-Sts')
    open_sts = C(EpicsSignalRO, 'Sw:Opn1-Sts')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._st = None
        self._target = None
        self.close_sts.subscribe(self._watcher_close,
                                 self.close_sts.SUB_VALUE)

        self.open_sts.subscribe(self._watcher_open,
                                 self.open_sts.SUB_VALUE)

    def set(self, value, *, wait=False, **kwargs):
        if value not in ('Open', 'Close'):
            raise ValueError(
                "must be 'Open' or 'Close', not {!r}".format(value))
        if wait:
            raise RuntimeError()
        if self._st is not None:
            raise RuntimeError()
        self._target = value
        self._st = st = DeviceStatus(self, timeout=None)
        self.cmd.put(value)

        return st

    def _watcher_open(self, *, old_value=None, value=None, **kwargs):
        print("in open watcher", old_value, value)
        if self._target != 'Open':
            return
        if self._st is None:
            return

        if new_value:
            self._st._finished()
            self._target = None
            self._st = None
        print("in open watcher")

    def _watcher_close(self, *, old_value=None, value=None, **kwargs):
        print("in close watcher", old_value, value)
        if self._target != 'Close':
            return

        if self._st is None:
            return

        if new_value:
            self._st._finished()
            self._target = None
            self._st = None

        pass


class SavedImageSignal(Signal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stashed_datakey = {}

    def describe(self):
        ret = super().describe()
        ret[self.name].update(self.stashed_datakey)
        return ret


def take_dark(cam, light_field, dark_field_name):
    # close shutter

    # take the dark frame
    cam.stage()
    st = cam.trigger()
    while not st.done:
        ttime.sleep(.1)
    ret = cam.read()
    desc = cam.describe()
    cam.unstage()

    # save the df uid
    df = ret[light_field]
    df_sig = getattr(cam, dark_field_name)
    df_sig.put(**df)
    # save the darkfrom description
    df_sig.stashed_datakey = desc[light_field]




class XPDTIFFPlugin(TIFFPlugin, FileStoreTIFFSquashing,
                    FileStoreIterativeWrite):
    pass


class XPDHDF5Plugin(HDF5Plugin, FileStoreHDF5IterativeWrite):
    pass


class XPDPerkinElmer(PerkinElmerDetector):
    image = C(ImagePlugin, 'image1:')

    tiff = C(XPDTIFFPlugin, 'TIFF1:',
             write_path_template='H:/pe1_data/%Y/%m/%d/',
             read_path_template='/direct/XF28ID1/pe1_data/%Y/%m/%d/',
             cam_name='cam',  # used to configure "tiff squashing"
             proc_name='proc',  # ditto
             read_attrs=[],
             root='/direct/XF28ID1/',
             fs=db.fs)

    # hdf5 = C(XPDHDF5Plugin, 'HDF1:',
    #          write_path_template='G:/pe1_data/%Y/%m/%d/',
    #          read_path_template='/direct/XF28ID1/pe1_data/%Y/%m/%d/',
    #          root='/direct/XF28ID1/', fs=db.fs)

    proc = C(ProcessPlugin, 'Proc1:')

    # These attributes together replace `num_images`. They control
    # summing images before they are stored by the detector (a.k.a. "tiff
    # squashing").
    images_per_set = C(Signal, value=1, add_prefix=())
    number_of_sets = C(Signal, value=1, add_prefix=())

    stats1 = C(StatsPlugin, 'Stats1:')
    stats2 = C(StatsPlugin, 'Stats2:')
    stats3 = C(StatsPlugin, 'Stats3:')
    stats4 = C(StatsPlugin, 'Stats4:')
    stats5 = C(StatsPlugin, 'Stats5:')

    roi1 = C(ROIPlugin, 'ROI1:')
    roi2 = C(ROIPlugin, 'ROI2:')
    roi3 = C(ROIPlugin, 'ROI3:')
    roi4 = C(ROIPlugin, 'ROI4:')

    # dark_image = C(SavedImageSignal, None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs.update([(self.cam.trigger_mode, 'Internal'),
                               ])



class ContinuousAcquisitionTrigger(BlueskyInterface):
    """
    This trigger mixin class records images when it is triggered.

    It expects the detector to *already* be acquiring, continously.
    """
    def __init__(self, *args, plugin_name=None, image_name=None, **kwargs):
        if plugin_name is None:
            raise ValueError("plugin name is a required keyword argument")
        super().__init__(*args, **kwargs)
        self._plugin = getattr(self, plugin_name)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._plugin.stage_sigs[self._plugin.auto_save] = 'No'
        self.cam.stage_sigs[self.cam.image_mode] = 'Continuous'
        self._plugin.stage_sigs[self._plugin.file_write_mode] = 'Capture'
        self._image_name = image_name
        self._status = None
        self._num_captured_signal = self._plugin.num_captured
        self._num_captured_signal.subscribe(self._num_captured_changed)
        self._save_started = False

    def stage(self):
        if self.cam.acquire.get() != 1:
            raise RuntimeError("The ContinuousAcuqisitionTrigger expects "
                               "the detector to already be acquiring.")
        return super().stage()
        # put logic to look up proper dark frame
        # die if none is found

    def trigger(self):
        "Trigger one acquisition."
        if not self._staged:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")
        self._save_started = False
        self._status = DeviceStatus(self)
        self._desired_number_of_sets = self.number_of_sets.get()
        self._plugin.num_capture.put(self._desired_number_of_sets)
        self.dispatch(self._image_name, ttime.time())
        # reset the proc buffer, this needs to be generalized
        self.proc.reset_filter.put(1)
        self._plugin.capture.put(1)  # Now the TIFF plugin is capturing.
        return self._status

    def _num_captured_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire' signal changes."
        if self._status is None:
            return
        if value == self._desired_number_of_sets:
            # This is run on a thread, so exceptions might pass silently.
            # Print and reraise so they are at least noticed.
            try:
                self.tiff.write_file.put(1)
            except Exception as e:
                print(e)
                raise
            self._save_started = True
        if value == 0 and self._save_started:
            self._status._finished()
            self._status = None
            self._save_started = False



class PerkinElmerContinuous(ContinuousAcquisitionTrigger, XPDPerkinElmer):
    pass


class PerkinElmerStandard(SingleTrigger, XPDPerkinElmer):
    pass


class PerkinElmerMulti(MultiTrigger, XPDPerkinElmer):
    shutter = C(EpicsSignal, 'XF:28IDC-ES:1{Sh:Exp}Cmd-Cmd')


pe1 = PerkinElmerStandard('XF:28IDC-ES:1{Det:PE1}', name='pe1', read_attrs=['tiff'],
                          configuration_attrs=['images_per_set', 'number_of_sets'])

pe1m = PerkinElmerMulti('XF:28IDC-ES:1{Det:PE1}', name='pe1', read_attrs=['tiff'],
                        configuration_attrs=['images_per_set', 'number_of_sets'],
                        trigger_cycle=[[('image', {shctl1: 1}),
                                        ('dark_image', {shctl1: 0})]])

pe1c = PerkinElmerContinuous('XF:28IDC-ES:1{Det:PE1}', name='pe1',
                             read_attrs=['tiff', 'stats1'],
                             configuration_attrs=['images_per_set', 'number_of_sets'],
                             plugin_name='tiff')
pe1.tiff.read_attrs = []  # don't include any signals, just the image itself
pe1c.tiff.read_attrs = []  # just the image
pe1c.stats1.read_attrs = ['total']

# some defaults, as an example of how to use this
# pe1.configure(dict(images_per_set=6, number_of_sets=10))
