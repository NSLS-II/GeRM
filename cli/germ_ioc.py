import curio
import curio.zmq as zmq
from caproto.curio.server import Context, find_next_tcp_port
from pygerm.caproto import GeRMIOC
from portable_fs.sqlite.fs import FileStore
import argparse

prefix = 'XF:28IDC-ES:1{Det:GeRM1}'

def create_server(zmq_url, fs):
    germ = GeRMIOC(zmq_url, fs)
    pvdb = {f'{prefix}:acquire': germ.acquire_channel,
            f'{prefix}:filepath': germ.filepath_channel,
            f'{prefix}:last_file': germ.last_file_channel,
            f'{prefix}:COUNT': germ.count_channel,
            f'{prefix}:UUID:CHIP': germ.uid_chip_channel,
            f'{prefix}:UUID:CHAN': germ.uid_chan_channel,
            f'{prefix}:UUID:TD': germ.uid_td_channel,
            f'{prefix}:UUID:PD': germ.uid_pd_channel,
            f'{prefix}:UUID:TS': germ.uid_ts_channel,
            }
    return Context('0.0.0.0', find_next_tcp_port(), pvdb), germ


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='IOC to front GeRM zmq server')
    parser.add_argument('host', type=str,
                        help='host running GeRM zmq server')
    args = parser.parse_args()

    zmq_ip = args.host

    fs = FileStore({'dbpath': '/tmp/fs.sqlite'})
    ctx, germ = create_server(f'tcp://{zmq_ip}', fs)

    async def runner():
        await curio.spawn(germ.zclient.read_forever, daemon=True)
        await ctx.run()

    zmq.run(runner)
