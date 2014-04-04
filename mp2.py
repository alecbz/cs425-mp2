#!/usr/bin/python
import argparse
import json
import multiprocessing
import socket
import random
import logging
from collections import namedtuple
import time

from unreliable_channel import UnreliableChannel
from reliable_channel import ReliableChannel
from casual_multicast_channel import CasualMulticastChannel
from total_ordering_multicast import TotalOrderingChannel

DEFAULT_PORT = 40060

Address = namedtuple('Address', ['ip', 'port'])

MESSAGES = ['a', 'b', 'c', 'd', 'e']


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
    if f:
        config = json.load(f)
        num_processes = config.get('num_processes', None)
        addresses = config.get('addresses', None)
        ordering = config.get('ordering', 'total')

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
        # for causal ordering, idx of the curr process in vector
        self.proc_idx = multiprocessing.current_process()._identity[0] - 1

        # initialized here because these launch threads
        self.reliable_channel = ReliableChannel(self.unreliable_channel)
        if self.ordering == 'total':
            self.total_ordering_channel = TotalOrderingChannel(self.reliable_channel, self.num_processes, self.addr, self.proc_idx)
        elif self.ordering == 'causal':
            self.casual_multicast_channel = CasualMulticastChannel(
                self.reliable_channel, self.proc_idx, len(self.addresses))
        else:
            print "Unknown ordering scheme '{}'".format(self.ordering)
            return 1

        logging.basicConfig(
            filename='{}.log'.format(self.port), level=logging.INFO)

        while True:
            group = self.addresses
            message = random.choice(MESSAGES)
            
            if self.ordering == 'total':
                self.total_ordering_channel.multicast(message, group, self.proc_idx)
            else:
                self.causal_multicast_channel.multicast(message, group)

            logging.info("Multicast message '%s' from %s to group %s",
                         message, self.addr, group)

            if self.ordering == 'total':
                if self.total_ordering_channel.can_recv():
                    addr, msg = self.total_ordering_channel.recv()
                    logging.info(
                        "Received multicast message '%s' from %s", msg, addr)
                time.sleep(5)
            else:
                if self.causal_multicast_channel.can_recv():
                    addr, msg = self.causal_multicast_channel.recv()
                    logging.info(
                        "Received multicast message '%s' from %s", msg, addr)



def main():
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
