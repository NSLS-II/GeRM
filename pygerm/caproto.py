import numpy as np
import h5py
from pathlib import Path
import caproto as ca
import curio
import curio.zmq as zmq
from pygerm.zmq import ZClient, DATA_TYPES
from pygerm import TRIGGER_SETUP_SEQ, START_DAQ, STOP_DAQ
import uuid


class ZClientCaproto(ZClient):
    def __init__(self, *args, max_events=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.acq_done = curio.Condition()
        self.collecting = False
        self.data_buffer = []
        self.last_frame = None
        self.max_events = max_events

    async def __cntrl_recv(self):
        msg = await self.ctrl_sock.recv()
        return np.frombuffer(msg, dtype=np.uint32)

    async def __cntrl_send(self, payload):
        payload = np.asarray(payload, dtype=np.uint32)
        return (await self.ctrl_sock.send(payload))

    async def read(self, addr):
        await self.__cntrl_send([0x0, addr, 0x0])
        return (await self.__cntrl_recv()[2])

    async def write(self, addr, value):
        await self.__cntrl_send([0x1, addr, value])
        # bounce the whole message back
        return (await self.__cntrl_recv())

    async def read_forever(self):
        while True:
            print(f'read forever {self.collecting}')
            # just read from the zmq socket
            topic, payload = await self.data_sock.recv_multipart()
            print(f'topic {topic}')
            # if we are not collecting, then bail and read again!
            if not self.collecting:
                continue
            # if we are collecting, unpack the payload
            topic, data = self.parse_message(topic, payload)
            if topic == self.TOPIC_META:
                self.last_frame = int(data)
                # if we saw a frame meta, we are done
                async with self.acq_done:
                    await self.acq_done.notify_all()
            elif topic == self.TOPIC_DATA:
                # if just data update the internal state
                self.data_buffer.append(data)
                new_ev = len(data[0])
                self.total_events += new_ev
            else:
                raise RuntimeError("should never get here")
            # if we have seen more than the maximum number of events
            if (self.max_events is not None and
                    self.total_events > self.max_events):
                # set the last frame to `None` (because we are now out
                # of sync!)
                self.last_frame = None
                # and report that we are done
                async with self.acq_done:
                    await self.acq_done.notify_all()

    async def trigger_frame(self):
        self.data_buffer.clear()
        self.total_events = 0
        self.collecting = True

        async with self.acq_done:
            await self.acq_done.wait()
            self.collecting = False

    async def read_frame(self):
        await self.trigger_frame()
        return self.last_frame, self.total_events, self.data_buffer


class ChannelGeRMAcquire(ca.ChannelData):
    def __init__(self, *, zclient,
                 parent, **kwargs):
        super().__init__(**kwargs)
        self.zclient = zclient
        self.parent = parent

    async def set_dbr_data(self, data, data_type, metadata):
        await super().set_dbr_data(data, data_type, metadata)
        if data:
            fr_num, ev_count, data = await triggered_frame(self.zclient)
            print(fr_num, ev_count)
            await self.parent.count_channel.set_dbr_data(
                ev_count, ca.DBR_INT.DBR_ID, None)
            try:
                write_path = self.parent.filepath_channel.value
                write_path = write_path.decode(
                    self.parent.filepath_channel.string_encoding)
                if write_path:
                    path = Path(write_path)
                    print(path)
                    path.mkdir(parents=True, exist_ok=True)

                    fname = path / '{}.h5'.format(str(uuid.uuid4()))
                    print(fname)
                    with h5py.File(str(fname), 'w-') as fout:
                        print('made file')
                        g = fout.create_group('GeRM')
                        dsets = {k: g.create_dataset(k, shape=(ev_count,),
                                                     dtype=f'uint{w}')
                                 for k, w in DATA_TYPES.items()}
                        print('made dsets')
                        offset = 0
                        for n, payload in enumerate(data):
                            print(f'bunch {n} with offset {offset}')
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

            except Exception as e:
                print(data_type)
                print('failed')
                print(e)

            await super().set_dbr_data(0, data_type, None)


class GeRMIOC:
    def __init__(self, zmq_url, fs):
        self._fs = fs
        self.zclient = ZClientCaproto(zmq_url, zmq=zmq)

        self.acquire_channel = ChannelGeRMAcquire(
            value=0, zclient=self.zclient, parent=self)

        self.filepath_channel = ca.ChannelString(
            value=b'/tmp', string_encoding='latin-1')
        self.last_file_channel = ca.ChannelString(
            value='null', string_encoding='latin-1')

        self.count_channel = ca.ChannelInteger(value=0)

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


async def triggered_frame(zc):
    for (addr, val) in TRIGGER_SETUP_SEQ:
        if addr is None:
            await curio.sleep(val)
        else:
            await zc.write(addr, val)

    await zc.write(*START_DAQ)
    fr_num, ev_count, data = await zc.read_frame()
    await zc.write(*STOP_DAQ)

    return fr_num, ev_count, data


async def runner(germ):
    await curio.spawn(germ.zclient.read_forever, daemon=True)
    return await triggered_frame(germ.zclient)
