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
from b_multicast_channel import BMulticastChannel

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
        # initialize vector
        self.msg_vector = [0] * len(addresses)

    def run(self):
        # for causal ordering, idx of the curr process in vector
        self.proc_idx = multiprocessing.current_process()._identity[0] - 1
        # initialized here because this launches a thread
        self.reliable_channel = ReliableChannel(
            self.unreliable_channel, self.ordering_scheme, self.msg_vector)
        self.b_multicast_channel = BMulticastChannel(self.reliable_channel)

        while True:
            # print str(self.port) + " " +  str(self.msg_vector)
            num_processes_in_group = random.randint(1, len(self.addresses) - 1)
            group = random.sample(self.peers, num_processes_in_group)

            message = random.choice(MESSAGES)
            if self.ordering_scheme == "fifo_ordering":
                # message is one of [A,B,...E]
                self.b_multicast_channel.multicast(
                    message, group, None, self.proc_idx)
                print "multicasting from " + str(self.port) + " to: " + str(group) + " the message " + message
                self.text_file.write("multicasting from " + str(self.port)
                                     + " to: " + str(group) + " the message " + message + "\n")
            elif self.ordering_scheme == "causal_ordering":
                self.msg_vector[self.proc_idx] = self.msg_vector[
                    self.proc_idx] + 1
                # stalls here
                self.b_multicast_channel.multicast(
                    message, group, self.msg_vector, self.proc_idx)
                print "multicasting from " + str(self.port) + " to: " + str(group) + " the message " + message
                self.text_file.write("multicasting from " + str(self.port) + " to: " + str(group)
                                     + " the message " + message + " current vec: " + str(self.msg_vector) + "\n")
            self.text_file.flush()
            if self.b_multicast_channel.delivered.not_empty:
                if self.ordering_scheme == "fifo_ordering":
                    self.text_file.write(
                        "Received " + str(self.b_multicast_channel.recv()) + "\n")
                elif self.ordering_scheme == "causal_ordering":
                    self.text_file.write("Received " + str(self.b_multicast_channel.recv())
                                         + " current vec: " + str(self.msg_vector) + "\n")
                self.text_file.flush()
            time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--delay',
        metavar='seconds',
        help='average delay time',
        type=float, default=0.2)
    parser.add_argument(
        '--drop_rate',
        metavar='probability',
        help='chance that a message will be dropped',
        type=float, default=0.1)
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
