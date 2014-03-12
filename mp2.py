import argparse
import json
import random
import multiprocessing
import select
import socket
import time
from collections import namedtuple
from sys import argv, stdin

DEFAULT_PORT = 10000

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
    num_processes = None
    addresses = None

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

    def __init__(self, port, addresses, drop_rate, delay):
        super(Process, self).__init__()
        self.port = port
        self.addresses = addresses
        self.drop_rate = drop_rate
        self.delay = delay
        self.peers = [
            addr for addr in self.addresses if addr != (local_ip(), self.port)]

        # set up our UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))

        # create a poll set
        self.poll = select.poll()
        self.poll.register(self.sock.fileno(), select.POLLIN)

    def send_message(self, message, addr):
        if random.random() < self.drop_rate:
            time.sleep(random.uniform(0, 2 * self.delay))
            self.sock.sendto(message, addr)

    def run(self):
        while True:
            if random.randrange(2):
                addr = random.choice(self.peers)
                message = random.choice(MESSAGES)
                self.send_message(message, addr)
            elif self.poll.poll(0):
                    data, addr = self.sock.recvfrom(1024)
                    print "Got message '%s' from %r" % (data, addr)


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
    processes = [Process(addr.port, addresses, args.drop_rate, args.delay)
                 for addr in addresses if addr.ip == local_ip()]
    for p in processes:
        p.start()
    for p in processes:
        p.join()


if __name__ == '__main__':
    main()
