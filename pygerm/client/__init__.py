import numpy as np
from collections import OrderedDict


def parse_event_payload(data):
    '''Split up the raw data coming over the socket.

    The documentation describes the data as 2 32 bit words with have
    been merged here into a single 64 bit value.

    The layout is

       "0" [[4 bit chip addr] [5 bit channel addr]] [10 bit TD] [12 bit PD]
       "1" [31 bit time stamp]

    '''

    # TODO sort out if this can be made faster!

    # chip addr
    chip = (data >> (27)) & 0xf
    # chan addr
    chan = (data >> (22)) & 0x1f
    # fine ts
    td = (data >> (12)) & 0x3ff
    # evergy readings
    pd = (data) & 0xfff
    # FPGA tick
    ts = data >> 32 & 0x7fffffff

    return chip, chan, td, pd, ts


DATA_TYPES = OrderedDict((('chip', 8),
                          ('chan', 8),
                          ('timestamp_fine', 16),
                          ('energy', 16),
                          ('timestamp_coarse', 32)))

# build a lookup table of the data types listed in zmq.py
DATA_TYPEMAP = {name: num for num, name in enumerate(list(DATA_TYPES))}


class ZClient:
    '''Base class for talking to the Zync chip

    '''
    ZMQ_DATA_PORT = "5556"
    ZMQ_CNTL_PORT = "5555"
    TOPIC_DATA = b"data"
    TOPIC_META = b"meta"

    def __init__(self, url, *, zmq):
        self.__context = zmq.Context()
        self._data_sock_class = zmq.SUB
        self.data_sock = self.__context.socket(self._data_sock_class)
        self.ctrl_sock = self.__context.socket(zmq.REQ)
        self.udp_ctrl_sock = self.__context.socket(zmq.REQ)

        self.data_sock.connect("{}:{}".format(url, self.ZMQ_DATA_PORT))
        self.data_sock.setsockopt(zmq.SUBSCRIBE, self.TOPIC_DATA)
        self.data_sock.setsockopt(zmq.SUBSCRIBE, self.TOPIC_META)

        self.ctrl_sock.connect("{}:{}".format(url, self.ZMQ_CNTL_PORT))

    def parse_message(self, topic, payload):

        if topic == self.TOPIC_DATA:
            payload = parse_event_payload(
                np.frombuffer(payload, np.uint64))
        else:
            payload = np.frombuffer(payload, np.uint32)
        return topic, payload

    def refresh_data_sock(self):
        print('a')
        self.data_sock.close(linger=0)
        print('b')
        try:
            self.data_sock = self.__context.socket(self._data_sock_class)
        except Exception as e:
            print(e)
            print('failed to remake socket')
        print('c')


class ZClientUDP(ZClient):
    ZMQ_UDP_CNTL_PORT = "5557"

    def __init__(self, url, *, zmq):
        super().__init__(url, zmq=zmq)
        self.udp_ctrl_sock.connect("{}:{}".format(url, self.ZMQ_UDP_CNTL_PORT))


class UClient:
    '''Base class for talking to the udp collector

    '''
    ZMQ_CNTL_PORT = "5557"

    def __init__(self, url, *, zmq):
        self.__context = zmq.Context()
        self.ctrl_sock = self.__context.socket(zmq.REQ)
        self.ctrl_sock.connect("{}:{}".format(url, self.ZMQ_CNTL_PORT))
