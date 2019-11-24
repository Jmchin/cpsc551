#!/usr/bin/env python3

import sys
import struct
import socket
# import code
import proxy
import config

# per <https://en.wikipedia.org/wiki/User_Datagram_Protocol>
MAX_UDP_PAYLOAD = 65507
config = config.read_config()

ts_name      = config['name']
adapter_host = config['adapter']['host']
adapter_port = config['adapter']['port']

adapter_uri = f'http://{adapter_host}:{adapter_port}'
ts = proxy.TupleSpaceAdapter(adapter_uri)

print(f'Connected to tuplespace {ts_name} on {adapter_uri}')

# code.interact(local=locals())

def main(address, port):
    # See <https://pymotw.com/3/socket/multicast.html> for details
    print("Here is my port:", int(port))
    server_address = ('', int(port))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)

    group = socket.inet_aton(address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"Listening on udp://{address}:{port}")

    try:
        while True:
            data, _ = sock.recvfrom(MAX_UDP_PAYLOAD)
            notification = data.decode()
            user, event, text = notification.split(" ", 2)
            notificationList = [user, event, text]

            #BIG PROBLEM: Endless writting of the tuplespace
            # write out to other tuplespaces
            # print(f'This is a(n) {event} event!')
            if event == 'adapter' or event == 'start':
                # TODO: either 'adapter' or 'start' was received and replication needs to be performed
                pass
            elif event.strip() == 'write':
                listToWrite = tuple(eval(notificationList[2]))
                ts._out(listToWrite)
            elif event.strip() == 'take':
                listToTake = tuple(eval(notificationList[2]))
                ts._in(listToTake)
            else:
                pass

    except Exception as e:
        print(e)
        sock.close()


def usage(program):
    print(f'Usage: {program} ADDRESS PORT', file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    print(*sys.argv[1:3])
    sys.exit(main(sys.argv[1], sys.argv[2]))
