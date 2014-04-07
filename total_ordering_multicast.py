import threading

from Queue import Queue
from Queue import PriorityQueue
from collections import namedtuple, defaultdict
from reliable_channel import ReliableChannel
from PriorityDictionary import priorityDictionary

# message sent on first multicast
MulticastMessage = namedtuple(
    'MulticastMessage', [
        'data', 'msg_id', 'deliverable'])
# message sent in response to multicast by recipient, contains proposed seq
Proposal = namedtuple('Proposal', ['seq', 'msg_id', 'addr'])
# message that is stored in the priority queue
MarkedMessage = namedtuple('MarkedMessage', ['seq', 'data', 'msg_id', 'addr'])


class TotalOrderingChannel:

    def __init__(self, reliable_channel, num_processes, addr):

        self.num_processes = num_processes
        self.addr = addr
        self.delivered = priorityDictionary()
        self.reliable_channel = reliable_channel
        self.seq = 0
        # maps from msg id to Proposals
        self.response_dict = defaultdict(list)
        # maps from msg id to MulticastMessage
        self.msg_dict = {}
        self.id_count = 0
        # maps from message id to number of messages in msg group
        self.group_size_dict = defaultdict(int)
        # dictionary from addr to heaps of message
        self.undeliverable_dict = defaultdict(list)
        self.delivered_lock = threading.Lock()
        self.group_size_lock = threading.Lock()
        # target is the callable object to be invoked in a separate thread on
        # start()
        self.listener = threading.Thread(target=self.listen)
        self.listener.daemon = True
        self.listener.start()

    def listen(self):
        while True:
            addr, msg = self.reliable_channel.recv()
            if isinstance(msg, MulticastMessage):
                self.seq += 1
                # keep the same msg id as the multicastmessage.
                proposal = Proposal(
                    self.seq, msg.msg_id, self.addr)
                # send proposal back to initiator
                self.reliable_channel.unicast(proposal, addr)
                with self.delivered_lock:
                    self.delivered[addr, msg] = self.seq
            elif isinstance(msg, Proposal):
                # get all the proposal of processes that you sent the
                # message to
                self.response_dict[msg.msg_id].append(msg)
                list_of_responses = self.response_dict[msg.msg_id]
                with self.group_size_lock:
                    msg_group_size = self.group_size_dict[msg.msg_id]
                if len(list_of_responses) == msg_group_size:
                    # the final priority that you will send back will be
                    # the max of the seq
                    final_priority = max(
                        list_of_responses, key=lambda x: x.seq)
                    final_msg = MarkedMessage(
                        final_priority.seq,
                        self.msg_dict[
                            msg.msg_id],
                        msg.msg_id,
                        self.addr)
                    # recreate the group of processes to send a final
                    # priority
                    group = [
                        proposal.addr for proposal in list_of_responses]
                    self.final_multicast(final_msg, group)
            elif isinstance(msg, MarkedMessage):
                # means you received the final priority
                # keep track of the latest sequence number heard so far
                self.seq = max(msg.seq, self.seq)
                updated_message = MulticastMessage(
                    msg.data.data,
                    msg.data.msg_id,
                    True)
                with self.delivered_lock:
                    del self.delivered[(addr, msg.data)]
                    self.delivered[(addr, updated_message)] = msg.seq

    def can_recv(self):
        with self.delivered_lock:
            if self.delivered:
                addr, retmessage = self.delivered.smallest()
                if retmessage.deliverable:
                    return True
            return False

    def recv(self):
        with self.delivered_lock:
            addr, msg = self.delivered.smallest()
            del self.delivered[addr, msg]
        return addr, msg.data

    def multicast(self, obj, group):
        # msg_id starts at 0
        with self.group_size_lock:
            self.group_size_dict[self.id_count] = len(group)
        msg = MulticastMessage(obj, self.id_count, False)
        # store the message. will contain every message you send
        self.msg_dict[self.id_count] = msg
        for addr in group:
            self.reliable_channel.unicast(msg, addr)
        self.id_count += 1

    def final_multicast(self, msg, group):
        for addr in group:
            self.reliable_channel.unicast(msg, addr)
