from Queue import Queue
from collections import namedtuple
from reliable_channel import ReliableChannel

Message = namedtuple('Message', ['seq', 'data', 'group'])


class ReliableMulticastChannel:

    def __init__(self, reliable_channel):
        self.delivered = Queue()
        self.reliable_channel = reliable_channel
        self.received = set()
        self.seq = 0

        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

    def listen(self):
        while True:
            msg, addr = self.reliable_channel.recv()
            if not (msg, addr) in self.received:
                self.received.add((msg, addr))
                for other in msg.group:
                    self.reliable_channel.unicast(msg, other)
                self.delivered.put((msg, addr))

    def recv(self):
        return self.delivered.get()

    def multicast(self, obj, group):
        self.seq += 1
        msg = Message(self.seq, obj, group)
        for addr in group:
            self.reliable_channel.unicast(msg, addr)
