import numpy as np
import h5py
from pathlib import Path
import caproto as ca
import uuid
import time
import curio
import curio.zmq as zmq
from .client import DATA_TYPES
from .client.curio_zmq import ZClientCurio, ZClientCurioBase, UClientCurio
from . import TRIGGER_SETUP_SEQ, START_DAQ, STOP_DAQ


class ChannelGeRMAcquireUDP(ca.ChannelData):
    def __init__(self, *, zclient, uclient, parent, **kwargs):
        super().__init__(**kwargs)
        self.zclient = zclient
        self.uclient = uclient
        self.parent = parent

    async def set_dbr_data(self, data, data_type, metadata):
        await super().set_dbr_data(data, data_type, metadata)

    async def trigger_frame(self):
        zc = self.zclient
        uc = self.uclient

        for (addr, val) in TRIGGER_SETUP_SEQ:
            if addr is None:
                await curio.sleep(val)
            else:
                await zc.write(addr, val)

        await uc.ctrl_sock.send(b'/tmp/test')
        await uc.ctrl_sock.recv()
        await zc.write(*START_DAQ)
        await uc.ctrl_sock.send(b'ack')
        await uc.ctrl_sock.recv()
        await uc.ctrl_sock.send(b'ack')
        await uc.ctrl_sock.recv()
        await zc.write(*STOP_DAQ)

        fr_num, ev_count, overfill = 0, 0, 0

        return fr_num, ev_count, overfill


class ChannelGeRMAcquire(ca.ChannelData):
    def __init__(self, *, zclient,
                 parent, **kwargs):
        super().__init__(**kwargs)
        self.zclient = zclient
        self.parent = parent

    async def set_dbr_data(self, data, data_type, metadata):
        await super().set_dbr_data(data, data_type, metadata)
        if data:
            start_time = time.time()
            fr_num, ev_count, data, overfill = (
                await self.zclient.triggered_frame())
            delta_time = time.time() - start_time
            print(f'read frame: {fr_num} with {ev_count} '
                  f'events in {delta_time}s ({ev_count / delta_time} ev/s )')
            await self.parent.count_channel.set_dbr_data(
                ev_count, ca.DBR_INT.DBR_ID, None)
            await self.parent.overfill_channel.set_dbr_data(
                overfill, ca.DBR_INT.DBR_ID, None)
            await self.parent.last_frame_channel.set_dbr_data(
                fr_num, ca.DBR_INT.DBR_ID, None)
            try:
                start_time = time.time()
                write_path = self.parent.filepath_channel.value
                write_path = bytes(write_path).decode('utf-8').strip('\x00')
                if len(write_path):
                    path = Path(write_path)
                    path.mkdir(parents=True, exist_ok=True)

                    fname = path / '{}.h5'.format(str(uuid.uuid4()))
                    with h5py.File(str(fname), 'w-') as fout:
                        g = fout.create_group('GeRM')
                        dsets = {k: g.create_dataset(k, shape=(ev_count,),
                                                     dtype=f'uint{w}')
                                 for k, w in DATA_TYPES.items()}
                        offset = 0
                        for n, payload in enumerate(data):
                            bunch_len = len(payload[0])
                            for k, d in zip(DATA_TYPES, payload):
                                dsets[k][offset:offset+bunch_len] = d
                            offset += bunch_len
                    await self.parent.last_file_channel.set_dbr_data(
                        str(fname.name), ca.DBR_STRING.DBR_ID, None)
                    if self.parent._fs:
                        fs = self.parent._fs
                        res = fs.insert_resource('GeRM',
                                                 str(fname), {}, '/')
                        for short, dset in zip(
                                ('chip', 'chan', 'td', 'pd', 'ts'),
                                DATA_TYPES):
                            chan_name = f'uid_{short}_channel'
                            chan = getattr(self.parent, chan_name)
                            dset_uid = str(uuid.uuid4())
                            fs.insert_datum(res, dset_uid, {'column': dset})

                            await chan.set_dbr_data(
                                dset_uid, ca.DBR_STRING.DBR_ID, None)
                delta_time = time.time() - start_time
                print(f'wrote frame: {fr_num} with {ev_count} '
                      f'events in {delta_time}s '
                      f'({ev_count / delta_time} ev/s )')

            except Exception as e:
                print(data_type)
                print('failed')
                print(e)

            await super().set_dbr_data(0, data_type, None)


class ChannelGeRMFrameTime(ca.ChannelDouble):

    RESOLUTION = 4e-8  # 40 ns
    MAXT = (2**32 - 1) * RESOLUTION

    def __init__(self, zclient, *, units='s', **kwargs):
        kwargs.setdefault('precision', 3)
        kwargs.setdefault('lower_ctrl_limit', 0)
        kwargs.setdefault('upper_ctrl_limit', self.MAXT)
        super().__init__(units=units, **kwargs)
        self.zclient = zclient

    async def set_dbr_data(self, data, data_type, metadata):
        data, = data

        if data > self.MAXT or data < 0:
            # TODO set an alarm or something
            return
        counts = data / self.RESOLUTION
        await self.zclient.write(0xd4, np.int32(counts))
        ret = await super().set_dbr_data(data, data_type, metadata)
        return ret

    async def get_dbr_data(self, type_):
        v = await self.zclient.read(0xd4)
        v *= self.RESOLUTION
        self.value = [v, ]
        ret = await super().get_dbr_data(type_)
        return ret


class GeRMIOCBase:
    def __init__(self, *, fs):
        self._fs = fs

        # this assumes a sub-class creates self.zclient and then calls
        # super()
        self.frametime_channel = ChannelGeRMFrameTime(
            value=1, zclient=self.zclient)

        self.filepath_channel = ca.ChannelChar(
            value='/tmp', string_encoding='latin-1')
        self.last_file_channel = ca.ChannelString(
            value='null', string_encoding='latin-1')

        self.count_channel = ca.ChannelInteger(value=0)
        self.overfill_channel = ca.ChannelInteger(value=0)
        self.last_frame_channel = ca.ChannelInteger(value=0)

        self.uid_chip_channel = ca.ChannelString(
            value='null', string_encoding='latin-1')
        self.uid_chan_channel = ca.ChannelString(
            value='null', string_encoding='latin-1')
        self.uid_td_channel = ca.ChannelString(
            value='null', string_encoding='latin-1')
        self.uid_pd_channel = ca.ChannelString(
            value='null', string_encoding='latin-1')
        self.uid_ts_channel = ca.ChannelString(
            value='null', string_encoding='latin-1')


class GeRMIOCZMQData(GeRMIOCBase):
    def __init__(self, zync_url, fs):
        self.zclient = ZClientCurio(zync_url, zmq=zmq)

        super().__init__(fs=fs)

        self.acquire_channel = ChannelGeRMAcquire(
            value=0, zclient=self.zclient, parent=self)


class GeRMIOCUDPData(GeRMIOCBase):
    def __init__(self, zync_url, udp_ctrl_url, fs):
        self.zclient = ZClientCurioBase(zync_url, zmq=zmq)
        self.udp_client = UClientCurio(udp_ctrl_url, zmq=zmq)

        super().__init__(fs=fs)

        self.acquire_channel = ChannelGeRMAcquireUDP(
            value=0, zclient=self.zclient, uclient=self.udp_client,
            parent=self)


async def runner(germ):
    await curio.spawn(germ.zclient.read_forever, daemon=True)
    return (await germ.zclient.triggered_frame())
