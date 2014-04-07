import threading

from Queue import Queue
from collections import defaultdict, namedtuple
from reliable_channel import ReliableChannel
# from vector_timestamp import VectorTimestamp

Message = namedtuple('Message', ['vector', 'data', 'sender', 'group'])


class CausalMulticastChannel:

    def __init__(self, reliable_channel, addr, addrs):
        # each processes' way of knowing what messages it has delivered
        self.delivered = Queue()

        self.reliable_channel = reliable_channel

        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

        # a map from groups to vector timestamps for that group
        self.vector = defaultdict(lambda: {addr: 0 for addr in addrs})

        self.addr = addr  # my address
        self.addrs = addrs  # all addresses

    def can_deliver(self, msg):
        vector = self.vector[msg.group]
        if vector[msg.sender] + 1 != msg.vector[msg.sender]:
            return False
        if any(msg.vector[addr] > vector[addr]
                for addr in self.addrs
                if addr != msg.sender):
            return False
        return True

    def listen(self):
        waiting = []

        while True:
            addr, msg = self.reliable_channel.recv()

            # check if we can deliver this message or need to buffer it
            if self.can_deliver(msg):
                self.delivered.put((addr, msg.data))
                self.vector[msg.group][msg.sender] += 1
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
        group = frozenset(group)  # make group hashable
        self.vector[group][self.addr] += 1
        msg = Message(self.vector[group], obj, self.addr, group)
        for addr in group:
            # stalls here
            self.reliable_channel.unicast(msg, addr)
