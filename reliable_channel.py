import threading
import random
import time
from collections import defaultdict, namedtuple
from heapq import *


Message = namedtuple('Message', ['seq', 'data'])
Ack = namedtuple('Ack', ['ack'])


class ReliableChannel:

    '''Building on top of UnreliableChannel, this channel supports
    guarenteed eventual delivery, FIFO delivery on a per-destination
    basis, and no duplicated delivery.'''

    def __init__(self, unreliable_channel):
        self.seq = defaultdict(int)
        self.unreliable_channel = unreliable_channel

        # a set of (addr, seq) pairs for which we've recieved acks
        self.acks = set([])
        self.acks_cond = threading.Condition()

        # a dictionary from addresses to heaps of messages
        self.messages = defaultdict(list)
        # a dictionary from addresses to the next sequence number to pop
        self.next_pop = defaultdict(lambda: 1)
        self.messages_cond = threading.Condition()

        self.listener = threading.Thread(target=self.listen)
        self.listener.daemon = True
        self.listener.start()

    def listen(self):
        while True:
            msg, addr = self.unreliable_channel.recv()
            if isinstance(msg, Ack):
                with self.acks_cond:
                    self.acks.add((addr, msg.ack))
                    self.acks_cond.notify()
            else:
                # create Ack response for sender
                ack = Ack(msg.seq)
                self.unreliable_channel.unicast(ack, addr)
                with self.messages_cond:
                    # if the msg sequence isn't earlier than next seq to pop,
                    # store it (otherwise we've already seen this message)
                    if not msg.seq < self.next_pop[addr]:
                        heappush(self.messages[addr], msg)
                        self.messages_cond.notify()

    def _available(self):
        return [(addr, heap) for (addr, heap) in self.messages.iteritems() if heap and heap[0].seq == self.next_pop[addr]]

    def can_recv(self):
        return bool(self._available())

    def recv(self):
        with self.messages_cond:
            available = self._available()
            while not available:
                self.messages_cond.wait()
                available = self._available()

            addr, heap = random.choice(available)
            msg = heappop(self.messages[addr])
            self.next_pop[addr] += 1
            return addr, msg.data

    def unicast(self, data, addr):
        self.seq[addr] += 1  # get the sequence number for this message
        msg = Message(self.seq[addr], data)
        while True:
            # send a message
            self.unreliable_channel.unicast(msg, addr)
            # wait for an ack with a timeout
            with self.acks_cond:
                max_wait = 2 * self.unreliable_channel.delay_avg
                start = time.time()
                # if addr and seq number aren't in acks set, wait until they
                # are
                while not ((addr, msg.seq) in self.acks) and (
                        time.time() - start < max_wait):
                    self.acks_cond.wait(0.1)
                # if ack has been received for a message to a addr, remove the
                # tuple
                if (addr, msg.seq) in self.acks:
                    self.acks.remove((addr, msg.seq))
                    return
