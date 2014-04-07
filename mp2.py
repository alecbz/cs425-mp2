#!/usr/bin/python
import argparse
import json
import multiprocessing
import socket
import random
import pickle
import os
from collections import namedtuple
from glob import glob
import time

from unreliable_channel import UnreliableChannel
from reliable_channel import ReliableChannel
from causal_multicast_channel import CausalMulticastChannel
from total_ordering_multicast import TotalOrderingChannel

DEFAULT_PORT = 40060

Address = namedtuple('Address', ['ip', 'port'])


def local_ip():
    # Taken from http://stackoverflow.com/a/166589/598940. A bit of a hack,
    # and requires internet access, but should be more robust than
    # socket.gethostbyname(socket.gethostname())

    if not hasattr(local_ip, 'ip'):
        print "Attempting to get local IP"
        s = socket.create_connection(('gmail.com', 80))
        local_ip.ip = s.getsockname()[0]
        s.close()
        print "Local IP is", local_ip.ip

    return local_ip.ip


def get_config(f):
    num_processes = None
    addresses = None
    ordering = 'total'

    if f:
        config = json.load(f)
        num_processes = config.get('num_processes', num_processes)
        addresses = config.get('addresses', addresses)
        ordering = config.get('ordering', ordering)

    if not num_processes:
        num_processes = len(addresses) if addresses else 6

    if addresses:
        assert len(num_processes) == len(ips)
        assert False, "Not supported"
    else:
        addresses = [Address(local_ip(), DEFAULT_PORT + i)
                     for i in range(num_processes)]

    return addresses, ordering


class Process(multiprocessing.Process):

    def __init__(self, port, addresses, drop_rate, delay, ordering):
        super(Process, self).__init__()
        self.port = port
        self.addr = (local_ip(), self.port)
        self.ordering = ordering
        self.addresses = addresses
        self.peers = [
            addr for addr in self.addresses if addr != self.addr]
        self.num_processes = len(self.addresses)

        # set up our UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        self.unreliable_channel = UnreliableChannel(
            self.sock, drop_rate, delay)

    def run(self):
        self.binary_log = open('{}.binlog'.format(self.port), 'w')

        # initialized here because these launch threads
        self.reliable_channel = ReliableChannel(self.unreliable_channel)

        self.vector = {addr: 0 for addr in self.addresses}
        if self.ordering == 'total':
            self.total_ordering_channel = TotalOrderingChannel(
                self.reliable_channel,
                self.num_processes,
                self.addr)
        elif self.ordering == 'causal':
            self.causal_multicast_channel = CausalMulticastChannel(
                self.reliable_channel, self.addr, self.addresses)
        else:
            print "Unknown ordering scheme '{}'".format(self.ordering)
            return 1

        while True:
            group = self.addresses

            self.vector[self.addr] += 1
            if self.ordering == 'total':
                # objects we send over the total ordering channel must be
                # hashable because of the PriorityDictionary
                to_send = tuple(self.vector.iteritems())
                self.total_ordering_channel.multicast(to_send, group)
            else:
                self.causal_multicast_channel.multicast(self.vector, group)

            vector = None
            if self.ordering == 'total':
                if self.total_ordering_channel.can_recv():
                    addr, recvd = self.total_ordering_channel.recv()
                    vector = dict(recvd)
                    print "{} received from {}".format(self.addr, addr)
                    pickle.dump((addr, vector), self.binary_log)
                    self.binary_log.flush()
            else:
                if self.causal_multicast_channel.can_recv():
                    addr, vector = self.causal_multicast_channel.recv()
                    print "{} received from {}".format(self.addr, addr)
                    pickle.dump((addr, vector), self.binary_log)
                    self.binary_log.flush()

            # update the vector timestamp
            if vector:
                for addr in vector:
                    if addr != self.addr:
                        self.vector[addr] = max(
                            vector[addr], self.vector[addr])
                    else:
                        self.vector[self.addr] += 1


def main():
    # clear logs from previous run
    for f in glob('*.log') + glob('*.binlog'):
        os.remove(f)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--delay',
        metavar='SECONDS',
        help='average delay time',
        type=float, default=0.2)
    parser.add_argument(
        '--drop_rate',
        help='chance that a message will be dropped',
        type=float, default=0.1)
    parser.add_argument('config_file', nargs='?', type=file)
    args = parser.parse_args()

    addresses, ordering = get_config(args.config_file)
    if args.config_file:
        args.config_file.close()

    processes = [Process(addr.port,
                         addresses,
                         args.drop_rate,
                         args.delay,
                         ordering)
                 for addr in addresses if addr.ip == local_ip()]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

if __name__ == '__main__':
    main()
