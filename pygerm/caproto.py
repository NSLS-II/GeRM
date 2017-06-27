import numpy as np
import h5py
from pathlib import Path
from caproto import ChannelData
import curio.zmq as zmq
from pygerm.zmq import ZClient, parse_event_payload, DATA_TYPES
from pygerm import TRIGGER_SETUP_SEQ, START_DAQ, STOP_DAQ
import curio


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


class ChannelGeRMAcquire(ChannelData):
    def __init__(self, *, zclient,
                 file_path_channel, **kwargs):
        super().__init__(**kwargs)
        self.zclient = zclient
        self.file_path_channel = file_path_channel

    async def set_dbr_data(self, data, data_type, metadata):
        await super().set_dbr_data(data, data_type, metadata)
        if data:
            fr_num, ev_count, data = await triggered_frame(self.zclient)
            print(fr_num, ev_count)
            try:
                print(self.file_path_channel)
                print(self.file_path_channel.value)
                if self.file_path_channel.value[0]:
                    path = Path(self.file_path_channel.value[0].decode(
                        self.file_path_channel.string_encoding))
                    print(path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    print(path.parent.exists())
                    with h5py.File(str(path), 'w-') as fout:
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
            except Exception as e:
                print(e)

            await super().set_dbr_data(0, data_type, metadata)


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


async def wrapped_run():
    zc = ZClientCaproto('tcp://localhost', zmq=zmq)

    t = await curio.spawn(triggered_frame, zc)
    return await t.join()
