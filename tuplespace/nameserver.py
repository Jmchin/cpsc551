#!/usr/bin/python

# nameserver.py

# This server program listens for tuplespace and adapter start events,
# and upon receipt persists the event to its own local tuplespace via
# XML-RPC.

# 1. nameserver binds a socket to listen for IP multicast traffic for
# the microblogging group.

# 2. inspects incoming notifcations, and logs all tuplespace and
# adapter start events

# 3. when receiving request from client for a username lookup, will
# return the address bound to the username, or throw a user not found
# exception


import sys
import struct
import socket
import proxy

MAX_UDP_PAYLOAD = 65507

ts = proxy.TupleSpaceAdapter("http://localhost:8001")

def main(address, port):

    server_address = ('', int(port))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind(server_address)

    group = socket.inet_aton(address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f'Listening on udp://{address}:{port}')

    try:
        while True:
            # listen for start events
            data, _ = sock.recvfrom(MAX_UDP_PAYLOAD)
            notification = data.decode()
            notif_lst = notification.split()

            # write start and adapter events to tuplespace
            if "start"   in notif_lst:
                ts._out(notif_lst)
            if "adapter" in notif_lst:
                ts._out(notif_lst)

    except Exception as e:
        print(e)
        sock.close()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage(sys.argv[0])

    sys.exit(main(*sys.argv[1:]))
