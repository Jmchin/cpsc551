#!/usr/bin/env python3

import sys
import socket
import proxy
import config


def main(tsName, topic, text):
    if len(sys.argv) < 3:
        return
    myTuple = (tsName, topic, text) = sys.argv[1:]
    # print(myTuple)

    # TODO: Don't connect directly to the nameserver's tuplespace
    # adapter, instead we want to open up a connection to the
    # nameserver middleware layer, which will handle all of our
    # requests

   # create connection to nameserver
    ts = proxy.TupleSpaceAdapter('http://localhost:8001')

    if ts._rdp((tsName, "adapter", str)) is not None:
        allTuples = ts._rdall((str, 'adapter', str))
        for tuple in allTuples:
            try:
                tsa = proxy.TupleSpaceAdapter(tuple[2])
                tsa._out(myTuple)
            except Exception as e:
                print(e)
    else:
        print(f'{tsName} does not exist.')


# TODO: Clean this up!
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("bad argument")
    sys.exit(main(*sys.argv[1:]))
