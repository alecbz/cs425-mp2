import threading

from Queue import Queue
from collections import namedtuple
from reliable_channel import ReliableChannel
from vector_timestamp import VectorTimestamp

Message = namedtuple('Message', ['vector', 'data', 'from_id'])


class CasualMulticastChannel:

    def __init__(self, reliable_channel, idx, num_processes):
        # each processes' way of knowing what messages it has delivered
        self.delivered = Queue()

        self.waiting = []
        self.waiting_cond = threading.Condition()

        self.reliable_channel = reliable_channel

        # target is the callable object to be invoked in a separate thread on
        # start()
        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

        self.vector = VectorTimestamp([0] * num_processes)

        self.idx = idx

    def listen(self):
        while True:
            addr, msg = self.reliable_channel.recv()

            # TODO: update vector tstamp

            # check if we can deliver this message or need to buffer it
            if self.vector >= msg.vector
                self.delivered.put((addr, msg))
            else:
                with self.waiting_cond:
                    self.waiting.append((addr, msg))

            # check if any previously buffered messages are now deliverable
            with self.waiting_cond:
                self.still_bad = []
                for addr, msg in self.waiting:
                    if self.vector >= msg.vector:
                        self.delivered.put((addr, msg))
                    else:
                        self.still_bad.append((addr, msg))
                self.waiting = self.still_bad

    def recv(self):
       return self.delivered.get()

    def multicast(self, obj, group):
        # group is a list
        msg = Message(self.vector, obj, self.idx)
        for addr in group:
            # stalls here
            self.reliable_channel.unicast(msg, addr)
