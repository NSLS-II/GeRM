import numpy as np
import h5py
from pathlib import Path
import caproto as ca
import curio.zmq as zmq
from pygerm.zmq import ZClient, parse_event_payload, DATA_TYPES
from pygerm import TRIGGER_SETUP_SEQ, START_DAQ, STOP_DAQ
import curio
import uuid


class ZClientCaproto(ZClient):

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

    async def read_frame(self):
        total_events = 0
        fr_num = None
        data_buffer = []
        while True:
            topic, data = await self.read_single_payload()
            if topic == self.TOPIC_META:
                print(data)
                fr_num = int(data)
                break
            elif topic == self.TOPIC_DATA:
                data_buffer.append(data)
                total_events += len(data[0])
            else:
                raise RuntimeError("should never get here")
        return fr_num, total_events, data_buffer

    async def read_single_payload(self):
        topic, payload = await self.data_sock.recv_multipart()

        if topic == self.TOPIC_DATA:
            payload = parse_event_payload(
                np.frombuffer(payload, np.uint64))
        else:
            payload = np.frombuffer(payload, np.uint32)
        return topic, payload


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
                        await self.parent.uid_chan_channel.set_dbr_data(
                            str(uuid.uuid4()), ca.DBR_STRING.DBR_ID, None)
                        await self.parent.uid_chip_channel.set_dbr_data(
                            str(uuid.uuid4()), ca.DBR_STRING.DBR_ID, None)
                        await self.parent.uid_td_channel.set_dbr_data(
                            str(uuid.uuid4()), ca.DBR_STRING.DBR_ID, None)
                        await self.parent.uid_pd_channel.set_dbr_data(
                            str(uuid.uuid4()), ca.DBR_STRING.DBR_ID, None)
                        await self.parent.uid_ts_channel.set_dbr_data(
                            str(uuid.uuid4()), ca.DBR_STRING.DBR_ID, None)

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
