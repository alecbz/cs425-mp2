import argparse
import os
import json
import multiprocessing
import socket
import signal
import random
import threading
import time
from collections import defaultdict, namedtuple
from sys import argv, stdin

from unreliable_channel import UnreliableChannel
from reliable_channel import ReliableChannel
from casual_multicast_channel import CasualMulticastChannel

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


def get_config():
    addresses = None
    num_processes = None

    if len(argv) >= 2:
        with open(argv[1], 'r') as f:
            config = json.load(f)
            num_processes = config.get('num_processes', None)
            addresses = config.get('addresses', None)

    if not num_processes:
        num_processes = len(addresses) if addresses else 5

    if addresses:
        assert len(num_processes) == len(ips)
        assert False, "Not supported"
    else:
        addresses = [Address(local_ip(), DEFAULT_PORT + i)
                     for i in range(num_processes)]

    return addresses


class Process(multiprocessing.Process):

    def __init__(self, port, addresses, drop_rate, delay, ordering_scheme):
        super(Process, self).__init__()
        self.port = port
        self.ordering_scheme = ordering_scheme
        self.addresses = addresses
        self.peers = [
            addr for addr in self.addresses if addr != (local_ip(), self.port)]

        # set up our UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        file_name = str(port) + ".log"
        self.text_file = open(file_name, 'w')
        self.unreliable_channel = UnreliableChannel(
            self.sock, drop_rate, delay)

    def run(self):
        # for causal ordering, idx of the curr process in vector
        self.proc_idx = multiprocessing.current_process()._identity[0] - 1
        # initialized here because this launches a thread
        self.reliable_channel = ReliableChannel(self.unreliable_channel)
        self.casual_multicast_channel = CasualMulticastChannel(
            self.reliable_channel, self.proc_idx, len(self.addresses))

        while True:
            group = self.addresses
            message = random.choice(MESSAGES)

            self.casual_multicast_channel.multicast(message, group)

            log_message = "multicast from {} to {} the message {}".format(
                self.port, group, message)
            print log_message
            print >>self.text_file, log_message

            if self.casual_multicast_channel.can_recv():
                addr, msg = self.casual_multicast_channel.recv()
                # print "Received {}".format(msg)
                print >>self.text_file, "Received {}".format(msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--delay',
        metavar='seconds',
        help='average delay time',
        type=float, default=0.0)
    parser.add_argument(
        '--drop_rate',
        metavar='probability',
        help='chance that a message will be dropped',
        type=float, default=0.0)
    args = parser.parse_args()

    addresses = get_config()
    processes = [Process(addr.port, addresses, args.drop_rate, args.delay, "causal_ordering")
                 for addr in addresses if addr.ip == local_ip()]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

if __name__ == '__main__':
    main()
