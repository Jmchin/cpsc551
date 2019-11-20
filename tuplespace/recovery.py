#!/usr/bin/env python3

import json
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

                # process the incoming notification
                notification = notification.replace(" ", ",", 2) # comma separate our three fields
                to_file = eval(notification)
                json.dump(to_file, log_file)

                print(notification)

                # TODO: Should we serialize this using JSON instead of a raw string?
                #
                # Right now we have a problem: Because we are writing
                # the received notification out as a string, we add an
                # additional burden on the server when we need to
                # deserialize the contents of a message to replay it
                # to a tuplespace. We lost all type information when
                # writing the event out as a string, so perhaps we
                # should use a different serialization format to
                # remove some of the parsing burden

                # Preliminary tests suggest that JSON is an adequate
                # serialization format for this purpose. We will
                # json.dumps(msg) upon receipt and then
                # json.loads(msg) for each line in the manifest when
                # replaying events

                # Recovery:
                #
                # The recovery feature should listen for an incoming
                # *adapter* event on the multicast group, attach to
                # the adapter located at *address*, and then replay
                # all *takes* and *writes* in the order they were
                # logged to the joining adapter/tuplespace pair.

                # Potential Issues:
                #
                # Right now we are only looking for the *adapter*
                # event, and are assuming that each adapter event is
                # associated with a paired tuplespace *start* event.
                # Obviously, if the associated tuplespace for the
                # adapter is not actually online, all tuplespace
                # operations will fail when trying to replay to the
                # server. Additional logic is needed here to handle
                # all the variable edge cases.

                # Because the recovery server is running on a single
                # thread of control, we will be unable to respond to
                # (i.e log) any multicast events while we are
                # recovering a tuplespace. Potential issues are to
                # create a queue for incoming requests to await
                # processing, or to spin off a separate thread for
                # each tuplespace that requires recovery.

                notif_tokens = notification.split()

                # TODO: Could probably spin up a new thread of control
                # so that the server can continue to log incoming
                # multicast events, and to replay events to multiple
                # joining servers to help alleviate the race condition
                if notif_tokens[1] == "adapter":
                    # TODO: This can probably be written better, but I
                    # didn't want to manually seek through the
                    # existing file object
                    with open(".manifest", mode='r') as m:
                        address = notif_tokens[2]

                        # connect to newly joined adapter
                        ts = proxy.TupleSpaceAdapter(address)

                        # read manifest in
                        lines = m.read().splitlines()

                        # filter out all nameserv references
                        lines = [l for l in lines if "nameserv" not in l]

                        # filter for all the writes and takes
                        lines = [l for l in filter(lambda li: "write" in li or "take" in li)]

                        # replay the events to the tuplespace
                        for line in lines:
                            tupl = line.split()
                            if tupl[1] == "write":
                                # TODO: parse msg portion back into a
                                # typed tuple

                                # Problems: Right now, the logging
                                # server will write the events it
                                # receives to file as a string. We
                                # need a good way to break the event
                                # into its three logical components
                                # (tuplespace-name, event, message)

                                # We cannot simply split on
                                # whitespace, because the message
                                # itself may contain whitespace.

                                # May be able to get around this
                                # problem by only splitting up to a
                                # '[' delimiter
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
