import threading

from Queue import Queue
from collections import defaultdict, namedtuple
from reliable_channel import ReliableChannel
from vector_timestamp import VectorTimestamp

Message = namedtuple('Message', ['vector', 'data', 'from_id', 'group'])


class CausalMulticastChannel:

    def __init__(self, reliable_channel, idx, num_processes):
        # each processes' way of knowing what messages it has delivered
        self.delivered = Queue()

        self.reliable_channel = reliable_channel

        # target is the callable object to be invoked in a separate thread on
        # start()
        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

        # a map from groups to vector timestamps for that group
        self.vector = defaultdict(lambda: VectorTimestamp([0] * num_processes))

        self.idx = idx
        self.num_processes = num_processes

    def can_deliver(self, msg):
        vector = self.vector[msg.group]
        if vector[msg.from_id] + 1 != msg.vector[msg.from_id]:
            return False
        if any(msg.vector[k] > vector[k]
                for k in range(self.num_processes)
                if k != msg.from_id):
            return False
        return True

    def listen(self):
        waiting = []

        while True:
            addr, msg = self.reliable_channel.recv()

            # check if we can deliver this message or need to buffer it
            if self.can_deliver(msg):
                self.delivered.put((addr, msg.data))
                self.vector[msg.group][msg.from_id] += 1
            else:
                waiting.append((addr, msg))

            # check if any previously buffered messages are now deliverable
            still_bad = []
            for addr, msg in waiting:
                if self.can_deliver(msg):
                    self.delivered.put((addr, msg.data))
                else:
                    still_bad.append((addr, msg))
            waiting = still_bad

    def can_recv(self):
        return not self.delivered.empty()

    def recv(self):
        return self.delivered.get()

    def multicast(self, obj, group):
        group = tuple(group)  # make group hashable
        self.vector[group][self.idx] += 1
        # group is a list
        msg = Message(self.vector[group], obj, self.idx, group)
        for addr in group:
            # stalls here
            self.reliable_channel.unicast(msg, addr)
