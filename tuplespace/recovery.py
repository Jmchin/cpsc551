#!/usr/bin/env python3

import json
import sys
import struct
import socket

import proxy

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

# TODO: Could probably spin up a new thread of control
# so that the server can continue to log incoming
# multicast events, and to replay events to multiple
# joining servers to help alleviate the race condition

# per <https://en.wikipedia.org/wiki/User_Datagram_Protocol>
MAX_UDP_PAYLOAD = 65507


def main(address, port):

    def replay_history(address):
        """ Replays microblog history to the adapter named by address """
        ts = proxy.TupleSpaceAdapter(address)

        with open(".manifest", mode='r') as m:
            # connect to newly joined adapter
            ts = proxy.TupleSpaceAdapter(address)
            # read file in as list of strings
            lines = m.read().splitlines()
            # read each line as json
            lines = [json.loads(l) for l in lines]
            # filter out nameserver
            lines = [l for l in lines if l['name'] is not "nameserv"]
            # filter for all the writes and takes
            lines = [l for l in filter(lambda li: "write"
                                        in li['event'] or "take" in
                                        li['event'], lines)]
            for line in lines:
                print(f'recovery: {line}')
                if line['event'] == 'write':
                    print(f'replaying {line["message"]} to {ts}')
                    # NOTE: eval is very fragile, is there a better
                    # way to do this?
                    ts._out(eval(line['message']))
                elif line['event'] == 'take':
                    print(f'replaying {line["message"]} to {ts}')
                    _ = ts._inp(eval(line['message']))  # we don't care about the return value
                else:
                    print("Something went wrong!")
                    return


    def notif_to_dict(notification):
        notification = notification.replace(" ", ",", 2) # comma separate our three fields
        notification = notification.split(",", 2)

        return { "name": notification[0],
                 "event": notification[1],
                 "message": notification[2]
        }

    ####################
    # BEGIN MAIN
    ####################

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
                data, _ = sock.recvfrom(MAX_UDP_PAYLOAD)
                notification = data.decode()
                notif_dict = notif_to_dict(notification)

                print(notif_dict)
                # log json to file
                log_file.write(json.dumps(notif_dict))
                log_file.write('\n')
                log_file.flush()
                # recover the adapter's tuplespace
                if notif_dict['event'] == "adapter":
                    replay_history(notif_dict['message'])
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
