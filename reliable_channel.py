import threading
import random
import time
import copy
from collections import defaultdict, namedtuple
from heapq import *


Message = namedtuple('Message', ['seq', 'data', 'id'])
Ack = namedtuple('Ack', ['ack'])


class ReliableChannel:

    '''Building on top of UnreliableChannel, this channel supports
    guarenteed eventual delivery, FIFO delivery on a per-destination
    basis, and no duplicated delivery.'''
    # changed based on ordering schemes

    def __init__(self, unreliable_channel, ordering_scheme="fifo_ordering", proc_idx=None, msg_vector=None):
        self.ordering_scheme = ordering_scheme
        if self.ordering_scheme == "fifo_ordering":
            self.seq = defaultdict(int)
        elif self.ordering_scheme == "causal_ordering":
            self.message_queue = []
        self.unreliable_channel = unreliable_channel
        self.proc_idx = proc_idx
        self.msg_vector = msg_vector
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

    def intlist_to_string(self, int_list):
        ret_str = ""
        for elem in int_list:
            ret_str = ret_str + str(elem)
        return ret_str

    def listen(self):
        while True:
            msg, addr = self.unreliable_channel.recv()
            # message is an Ack
            if isinstance(msg, Ack):
                with self.acks_cond:
                    self.acks.add((addr, msg.ack))
                    self.acks_cond.notify()
            # message isn't an Ack
            else:
                if self.ordering_scheme == "fifo_ordering":
                    # create Ack response for sender
                    ack = Ack(msg.seq)
                elif self.ordering_scheme == "causal_ordering":
                    vector_str = self.intlist_to_string(msg.data.vector)
                    ack = Ack(vector_str)
                self.unreliable_channel.unicast(ack, addr)
                with self.messages_cond:
                    # if the msg sequence isn't earlier than next seq to pop,
                    # store it. fifo ordering
                    if self.ordering_scheme == "fifo_ordering":
                        if not msg.seq < self.next_pop[addr]:
                            heappush(self.messages[addr], msg)
                    elif self.ordering_scheme == "causal_ordering":
                        self.message_queue.append(msg)

    def _available(self):
        # need to deepcopy so that size of dictionary does not change when
        # iterating
        if self.ordering_scheme == "fifo_ordering":
            messages_copy = copy.deepcopy(dict(self.messages))
            retlist = [(addr, heap)
                       for (addr, heap) in messages_copy.iteritems()
                       # if heap is non-empty and msg seq number equals the next
                       # seq number to be read
                       if heap and heap[0].seq == self.next_pop[addr]]
            return retlist
        elif self.ordering_scheme == "causal_ordering":
            message_q_copy = copy.deepcopy(list(self.message_queue))
            retlist = []
            if not message_q_copy:
                return []
            else:
                for msg in message_q_copy:
                    causal_cond = True
                    for i in range(0, len(self.msg_vector)):
                        if i != msg.data.id:
                            if self.msg_vector[i] < msg.data.vector[i]:
                                causal_cond = False
                                break
                    fifo_cond = (msg.data.vector[msg.id]
                                 == (self.msg_vector[msg.id] + 1))
                    if fifo_cond and causal_cond:
                        retlist.append((msg.data.id, msg))
                return retlist

    def can_recv(self):
        return bool(self._available())

    def recv(self):
        with self.messages_cond:
            available = self._available()
            while not available:
                self.messages_cond.wait()
                available = self._available()

            if self.ordering_scheme == "fifo_ordering":
                addr, heap = random.choice(available)
                msg = heappop(self.messages[addr])
                self.next_pop[addr] += 1
                return addr, msg.data
            elif self.ordering_scheme == "causal_ordering":
                from_id, msg = available.pop()
                self.message_queue.remove(msg)
                return from_id, msg.data, msg.vector

    # we need two different unicast functions for causal and total ordering

    def unicast_causal(self, data, addr, from_id):
        # what should replace the [0,0,0,0]?
        msg = Message([], data, from_id)
        while True:
            self.unreliable_channel.unicast(msg, addr)
            with self.acks_cond:
                max_wait = 2 * self.unreliable_channel.delay_avg
                start = time.time()
                vector_str = self.intlist_to_string(msg.data.vector)
                # if addr and seq number aren't in acks set, wait until they
                # are
                while not ((addr, vector_str) in self.acks) and (
                        time.time() - start < max_wait):
                    self.acks_cond.wait(0.1)
                # if ack has been received for a message to a addr, remove the
                # tuple
                if (addr, vector_str) in self.acks:
                    self.acks.remove((addr, vector_str))
                    return

    # data is Message(seq,[A,B..E],from_id)
    def unicast(self, data, addr, from_id=None):
        self.seq[addr] += 1  # get the sequence number for this message
        msg = Message(self.seq[addr], data, from_id)
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
