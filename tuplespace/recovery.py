#!/usr/bin/env python3

import sys
import struct
import socket

import proxy

# per <https://en.wikipedia.org/wiki/User_Datagram_Protocol>
MAX_UDP_PAYLOAD = 65507


def main(address, port):
    # See <https://pymotw.com/3/socket/multicast.html> for details

    # localhost:port
    server_address = ('', int(port))

    # create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # bind the socket to the server's address
    sock.bind(server_address)

    # define the multicast group
    group = socket.inet_aton(address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)

    # subscribe to the multicast group
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"Listening on udp://{address}:{port}")

    with open(".manifest", mode='w+') as log_file:
        try:
            while True:
                # print out all received UDP packets to the console
                data, _ = sock.recvfrom(MAX_UDP_PAYLOAD)
                notification = data.decode()
                print(notification)

                log_file.write(f'{notification}\n')
                log_file.flush()  # flush buffer to the file

                # begin recovery server

                # BUG: if tuplespace comes online without the
                # associated adapter event, then recovery never occurs
                if notification.split()[1] == "adapter":
                    with open(".manifest", mode='r') as m:
                        # connect to tuplespace adapter proxy
                        address = notification.split()[2]
                        ts = proxy.TupleSpaceAdapter(address)

                        # read manifest in
                        lines = m.read().splitlines()
                        for line in lines:
                            tupl = line.split()
                            if tupl[1] == "write":
                                out = tupl[2][1:-2]
                                out = out.split()
                                ts._out(tuple(out))
                            if tupl[1] == "take":
                                ts._in(tupl[2])
        except Exception as e:
            print(e)
            sock.close()


def usage(program):
    print(f'Usage: {program} ADDRESS PORT', file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage(sys.argv[0])

    sys.exit(main(*sys.argv[1:]))
