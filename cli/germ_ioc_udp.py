import curio.zmq as zmq
from caproto.curio.server import Context, find_next_tcp_port
from pygerm.caproto import GeRMIOCUDPData
# from databroker.assets.sqlite import Registry
import argparse

prefix = 'XF:28IDC-ES:1{Det:GeRM1}'


def create_server(zync_url, udp_url, reg):
    germ = GeRMIOCUDPData(zync_url, udp_url, reg)
    pvdb = {f'{prefix}:acquire': germ.acquire_channel,
            f'{prefix}:frametime': germ.frametime_channel,

            f'{prefix}:filepath': germ.filepath_channel,
            f'{prefix}:read_root': germ.readroot_channel,
            f'{prefix}:write_root': germ.writeroot_channel,

            f'{prefix}:src_mount': germ.srcmount_channel,
            f'{prefix}:dest_mount': germ.destmount_channel,

            f'{prefix}:last_file': germ.last_file_channel,

            f'{prefix}:overfill': germ.overfill_channel,
            f'{prefix}:last_frame': germ.last_frame_channel,
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
    parser.add_argument('zync_host', type=str,
                        help='ip of the Zync server')
    parser.add_argument('collector_host', type=str,
                        help='ip of the udp collector')
    args = parser.parse_args()

    zync_ip = args.zync_host
    collector_ip = args.collector_host

    # from metadataclient.mds import MDS
    from databroker import Broker
    db = Broker.named('xpd')
    reg = db.reg

    ctx, germ = create_server(f'tcp://{zync_ip}', f'tcp://{collector_ip}', reg)

    async def runner():
        await ctx.run()

    zmq.run(runner)
