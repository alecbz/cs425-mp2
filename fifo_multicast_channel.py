import threading

from Queue import Queue
from collections import namedtuple
from reliable_channel import ReliableChannel

Message = namedtuple('Message', ['seq', 'data', 'id'])


class FifoMulticastChannel:

    def __init__(self, reliable_channel):
        assert reliable_channel.ordering_scheme == "fifo_ordering"
        self.seq = 0

        # each processes' way of knowing what messages it has delivered
        self.delivered = Queue()
        self.reliable_channel = reliable_channel

        # target is the callable object to be invoked in a separate thread on
        # start()
        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

    def listen(self):
        while True:
            addr, msg = self.reliable_channel.recv()
            self.delivered.put((addr, msg))

    def recv(self):
        return self.delivered.get()

    def multicast(self, obj, group, from_id):
        # group is a list
        self.seq += 1
        msg = Message(self.seq, obj, from_id)
        for addr in group:
            self.reliable_channel.unicast(msg, addr, from_id)
