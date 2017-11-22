from . import ZClient, parse_event_payload
import numpy as np
import datetime


class ZClientWriter(ZClient):
    '''Synchronous class for accessing the ZMQ server that writes data files

    This is to maintain MARS_DAQ gui

    '''
    def __init__(self, connect_str):
        import zmq
        super().__init__(connect_str, zmq=zmq)

    def __cntrl_recv(self):
        msg = self.ctrl_sock.recv()
        dat = np.frombuffer(msg, dtype=np.uint32)
        return dat

    def __cntrl_send(self, payload):
        self.ctrl_sock.send(np.array(payload, dtype=np.uint32))

    def write(self, addr, value):
        self.__cntrl_send([0x1, int(addr), int(value)])
        self.__cntrl_recv()

    def read(self, addr):
        self.__cntrl_send([0x0, int(addr), 0x0])
        return int(self.__cntrl_recv()[2])

    def set_trigdaq(self, value):
        self.write(0x00, value)
        # print("Trigger DAQ")

    def get_data(self, chkdata):
        self.nbr = 0
        totallen = 0
        pd = []
        td = []
        addr = []
        start = datetime.datetime.now()

        print("In Get Data")
        with open('data_4.bin', 'wb') as fd:
            while True:
                [address, msg] = self.data_sock.recv_multipart()

                if msg == b'END':
                    print("Received %s messages" % str(self.nbr))
                    print("Message END received")
                    break
                if (address == self.TOPIC_META):
                    print("Meta data received")
                    meta_data = np.frombuffer(msg, dtype=np.uint32)
                    print(meta_data)
                    np.savetxt("meta.txt", meta_data, fmt="%x")
                    break
                if (address == self.TOPIC_DATA):
                    print("Event data received")
                    data = np.frombuffer(msg, dtype=np.uint64)
                    fd.write(data)
                    # counting number of words, getting words out as one
                    # 64bit number
                    totallen = totallen + len(data) * 2
                    print("Msg Num: %d, Msg len: %d, Tot len: %d" % (
                        self.nbr, len(data) * 2, totallen))

                    _chip, _chan, _td, _pd, _ = parse_event_payload(data)

                    pd.extend(_pd)
                    td.extend(_td)
                    addr.extend((_chan << 5) + _chip)

                    if self.nbr > 5000:
                        break
                    self.nbr += 1

        stop = datetime.datetime.now()

        elapsed = stop - start
        sec = elapsed.seconds + elapsed.microseconds*1.0e-6
        print("Processing time:", elapsed, sec)

        print("Total Size: %d (%d bytes)" % (totallen * 2, totallen * 8))
        bitrate = (totallen*2) / sec
        print('Received %d messages at %f MBps' % (self.nbr, bitrate))
        print('Received %d events at %f ev/s' % (len(pd), len(pd) / sec))

        return totallen, bitrate, pd, td, addr
