import numpy as np

from caproto import ChannelData, SubscriptionType
from curio.meta import awaitable
import curio.zmq as zmq
from pygerm.zmq import ZClient, parse_event_payload
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
    def __init__(self, *, zclient, **kwargs):
        super().__init__(**kwargs)
        self.zclient = zclient

    def set_dbr_data(self, data, data_type, metadata, future):
        raise NotImplemented()

    @awaitable(set_dbr_data)
    async def set_dbr_data(self, data, data_type, metadata, future):
        try:
            self.value = self.fromtype(values=data, data_type=data_type)
        except Exception as ex:
            future.set_exception(ex)
        else:
            sub_queue = self._subscription_queue
            if sub_queue is not None:
                sub_queue.put((self, SubscriptionType.DBE_VALUE,
                               self.value) +
                              self._subscription_queue_args)
        return True


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
