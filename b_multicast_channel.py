import threading

from Queue import Queue
from collections import namedtuple
from reliable_channel import ReliableChannel

Message = None


class BMulticastChannel:

    # changed already based on ordering scheme
    def __init__(self, reliable_channel):
        global Message
        self.ordering_scheme = reliable_channel.ordering_scheme
        # causal uses vector, total uses seq
        if self.ordering_scheme == "fifo_ordering":
            Message = namedtuple('Message', ['seq', 'data', 'id'])
            self.seq = 0
        elif self.ordering_scheme == "causal_ordering":
            Message = namedtuple('Message', ['vector', 'data', 'id'])

        # each processes' way of knowing what messages it has delivered
        self.delivered = Queue()
        self.reliable_channel = reliable_channel

        # target is the callable object to be invoked in a separate thread on
        # start()
        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

    # changed based on ordering scheme
    def listen(self):
        while True:
            # print self.reliable_channel.can_recv()
            # for some reason is always false
            if self.reliable_channel.can_recv():
                # print "able to receive"
                if self.ordering_scheme == "fifo_ordering":
                    addr, msg = self.reliable_channel.recv()
                    self.delivered.put((addr, msg))
                elif self.ordering_scheme == "causal_ordering":
                    addr, msg, vector = self.reliable_channel.recv()
                    self.delivered.put((addr, msg, vector))

    # nothing needs to be change here
    def recv(self):
        if self.ordering_scheme == "causal_ordering":
            addr, deliv_msg, vector = self.delivered.get()
            self.reliable_channel.msg_vector[deliv_msg.id] += 1
            return deliv_msg
        elif self.ordering_scheme == "fifo_ordering":
            return self.delivered.get()

    # changed based on ordering scheme
    # obj is one of [A,B,C...E]
    def multicast(self, obj, group, vector, from_id):
        # group is a list
        if self.ordering_scheme == "fifo_ordering":
            self.seq += 1
            msg = Message(self.seq, obj, from_id)
            for addr in group:
                self.reliable_channel.unicast(msg, addr, from_id)
        elif self.ordering_scheme == "causal_ordering":
            msg = Message(vector, obj, from_id)
            for addr in group:
                # stalls here
                self.reliable_channel.unicast_causal(msg, addr, from_id)
