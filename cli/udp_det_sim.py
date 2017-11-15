import asyncio
import zmq
import zmq.asyncio
import numpy as np
from enum import Enum
from collections import defaultdict
import time


class HSProtocol(asyncio.DatagramProtocol):
    '''Mock the high-speed UDP protocol from next round of GeRM


    '''

    def connection_made(self, transport):
        self.transport = transport


class CMDS(Enum):
    REG_READ = 0
    REG_WRITE = 1
    START_DMA = 2


FIFODATAREG = 24
FIFORDCNTREG = 25
FIFOCNTRLREG = 26

FRAMEACTIVEREG = 52
FRAMENUMREG = 54
FRAMELENREG = 53


ctx = zmq.asyncio.Context()
loop = zmq.asyncio.ZMQEventLoop()
asyncio.set_event_loop(loop)

# average number of events per msg
N = 50000
# number of messages
n_msgs = 50
# average total exposure
simulated_exposure = 10
# expected ticks between events
# ([S] / [event]) * ([tick] / [s]) = [tick] / [event]
tick_gap = int((simulated_exposure / N) / (40 * 10e-9))

n_chips = 12
n_chans = 32


def simulate_line(n, c):
    c = c.astype(float)
    return np.clip(
        (0.5 + 0.4 * np.sin((2*np.pi * 3 / (12*32)) * c)) *
        ((2**7 * np.random.randn(n)) + 2**11),
        0, 2**12 - 1).astype(np.uint64)


def simulate_random(n):
    return np.random.randint(2**12, size=n, dtype=np.uint64)


def make_sim_payload(num, n_chips, n_chans, tick_gap, ts_offset):
    pix_id = np.clip((50 * np.random.randn(num) + 192),
                     0, 383).astype(np.uint64)
    chip_id = pix_id // n_chans
    chan_id = pix_id % n_chans
    # fine timestamp
    td = np.random.randint(2**10, size=num, dtype=np.uint64) << (12)
    # energy
    pd = simulate_line(num, chip_id*32 + chan_id)
    # coarse timestamp
    ts = np.mod((np.cumsum(
        np.random.poisson(tick_gap, size=num).astype(np.uint64)) +
                 ts_offset),
                2**31) << 32
    payload = (chip_id << 27) + (chan_id << 22) + td + pd + ts
    return payload, ts[-1]


@asyncio.coroutine
def recv_and_process():
    responder = ctx.socket(zmq.REP)
    publisher = ctx.socket(zmq.PUB)
    responder.bind(b'tcp://*:5555')
    publisher.bind(b'tcp://*:5556')
    state = defaultdict(int)

    ts_offset = 0

    @asyncio.coroutine
    def sim_data():
        nonlocal ts_offset
        state[FRAMENUMREG] += 1
        num_per_msg = np.random.poisson(N, size=n_msgs)
        ts_offset = 0
        for num in num_per_msg:
            payload, ts_offset = make_sim_payload(num,
                                                  n_chips, n_chans,
                                                  tick_gap,
                                                  ts_offset)
            yield from publisher.send_multipart([b'data', payload])

        yield from publisher.send_multipart([b'meta',
                                             np.array([state[FRAMENUMREG], 0],
                                                      dtype=np.uint32)])
        return np.sum(num_per_msg, dtype=np.intp)

    while True:
        msg = yield from responder.recv_multipart()
        for m in msg:
            cmd, addr, value = np.frombuffer(m, dtype=np.int32)
            cmd = CMDS(cmd)
            if cmd == CMDS.REG_WRITE:
                state[addr] = value
                yield from responder.send(m)
                if addr == 0 and value == 1:
                    start_time = time.time()
                    num_ev = yield from sim_data()
                    delta_time = time.time() - start_time
                    print(f'generated {num_ev} events in {delta_time} s')
            elif cmd == CMDS.REG_READ:
                value = state[addr]
                reply = np.array([cmd.value, addr, value], dtype=np.uint32)
                yield from responder.send(reply)
            else:
                yield from responder.send(np.ones(3, dtype=np.uint32) * 0xdead)


loop.run_until_complete(recv_and_process())
