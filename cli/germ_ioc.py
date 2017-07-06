import curio
import curio.zmq as zmq
from caproto.curio.server import Context, find_next_tcp_port
from pygerm.caproto import GeRMIOC
from portable_fs.sqlite.fs import FileStore


def create_server(zmq_url, fs):
    germ = GeRMIOC(zmq_url, fs)
    pvdb = {'germ:acquire': germ.acquire_channel,
            'germ:filepath': germ.filepath_channel,
            'germ:last_file': germ.last_file_channel,
            'germ:COUNT': germ.count_channel,

            'germ:UUID:CHIP': germ.uid_chip_channel,
            'germ:UUID:CHAN': germ.uid_chan_channel,
            'germ:UUID:TD': germ.uid_td_channel,
            'germ:UUID:PD': germ.uid_pd_channel,
            'germ:UUID:TS': germ.uid_ts_channel,
            }
    return Context('0.0.0.0', find_next_tcp_port(), pvdb), germ


if __name__ == '__main__':
    fs = FileStore({'dbpath': '/tmp/fs.sqlite'})
    ctx, germ = create_server('tcp://10.0.143.160', fs)

    async def runner():
        await curio.spawn(germ.zclient.read_forever, daemon=True)
        await ctx.run()

    zmq.run(runner)

