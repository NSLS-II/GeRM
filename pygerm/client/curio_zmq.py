from . import ZClient
from .. import TRIGGER_SETUP_SEQ, START_DAQ, STOP_DAQ
import numpy as np
import curio


class ZClientCaprotoBase(ZClient):
    def __init__(self, *args, max_events=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.acq_done = curio.Condition()
        self.collecting = False
        self.data_buffer = []
        self.last_frame = None
        self.overfill = 0
        self.max_events = max_events
        self.cmd_lock = curio.Lock()

    async def __cntrl_recv(self):
        msg = await self.ctrl_sock.recv()
        return np.frombuffer(msg, dtype=np.uint32)

    async def __cntrl_send(self, payload):
        payload = np.asarray(payload, dtype=np.uint32)
        return (await self.ctrl_sock.send(payload))

    async def __udp_ctrl(self, payload):
        await self.udp_ctrl_sock.send(payload.encode())
        return (self.udp_ctrl_sock.recv())

    async def read(self, addr):
        async with self.cmd_lock:
            await self.__cntrl_send([0x0, addr, 0x0])
            ret = await self.__cntrl_recv()
            return ret[2]

    async def write(self, addr, value):
        print(f'writting addr 0x{addr:x} val {value}')
        async with self.cmd_lock:
            await self.__cntrl_send([0x1, addr, value])
            # bounce the whole message back
            ret = await self.__cntrl_recv()
            return ret

    async def set_filename(self, fname):
        return (await self.__udp_ctrl(fname))


class ZClientCaproto(ZClientCaprotoBase):
    async def read_forever(self):
        while True:
            # just read from the zmq socket
            topic, payload = await self.data_sock.recv_multipart()
            # if we are not collecting, then bail and read again!
            if not self.collecting:
                continue
            # if we are collecting, unpack the payload
            topic, data = self.parse_message(topic, payload)
            if topic == self.TOPIC_META:
                self.last_frame, self.overfill = data

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
        return (self.last_frame, self.total_events,
                self.data_buffer, self.overfill)

    async def triggered_frame(self):
        zc = self
        for (addr, val) in TRIGGER_SETUP_SEQ:
            if addr is None:
                await curio.sleep(val)
            else:
                await zc.write(addr, val)

        await zc.write(*START_DAQ)
        # cal pulse for debugging sometimes
        # await zc.write(0x10, 0xfff)
        # await zc.write(0x10, 0x0)
        fr_num, ev_count, data, overfill = await zc.read_frame()
        await zc.write(*STOP_DAQ)

        return fr_num, ev_count, data, overfill
