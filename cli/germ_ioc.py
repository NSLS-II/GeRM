import caproto as ca
from caproto.curio.server import Context, find_next_tcp_port
from pygerm.caproto import ChannelGeRMAcquire, ZClientCaproto
import curio.zmq as zmq


class GeRMIOC:
    def __init__(self, zmq_url):
        self.zclient = ZClientCaproto(zmq_url, zmq=zmq)
        self.filepath_channel = ca.ChannelString(
            value='a',
            string_encoding='latin-1')
        self.acquire_channel = ChannelGeRMAcquire(
            value=0,
            zclient=self.zclient,
            file_path_channel=self.filepath_channel)


if __name__ == '__main__':
    germ = GeRMIOC('tcp://localhost')
    pvdb = {'germ:acquire': germ.acquire_channel,
            'germ:filepath': germ.filepath_channel}

    ctx = Context('0.0.0.0', find_next_tcp_port(), pvdb)
    zmq.run(ctx.run())
