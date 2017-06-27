import curio.zmq as zmq
from caproto.curio.server import Context, find_next_tcp_port
from pygerm.caproto import GeRMIOC


def create_server(zmq_url):
    germ = GeRMIOC(zmq_url, None)
    pvdb = {'germ:acquire': germ.acquire_channel,
            'germ:filepath': germ.filepath_channel,
            'germ:last_file': germ.last_file_channel,
            'germ:datum_uid': germ.datum_uid_channel}

    return Context('0.0.0.0', find_next_tcp_port(), pvdb), germ


if __name__ == '__main__':
    ctx, germ = create_server('tcp://localhost')
    zmq.run(ctx.run())
