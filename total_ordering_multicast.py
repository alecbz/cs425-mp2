import threading

from Queue import Queue
from Queue import PriorityQueue
from collections import namedtuple,defaultdict
from reliable_channel import ReliableChannel


#message sent on first multicast 
MulticastMessage = namedtuple('MulticastMessage', ['data','msg_id'])
#message sent in response to multicast by recipient, contains proposed seq
Proposal = namedtuple('Proposal', ['seq','msg_id','addr'])
#message that is stored in the priority queue       
MarkedMessage = namedtuple('MarkedMessage', ['seq','data','msg_id','addr'])


class TotalOrderingChannel:

    def __init__(self, reliable_channel, num_processes, addr, from_id):
        
        self.num_processes = num_processes
        self.from_id = from_id      
        self.addr = addr
        self.delivered = PriorityQueue()
        self.undeliverable = []
        self.reliable_channel = reliable_channel
        self.seq = 0
        #maps from msg id to Proposals
        self.response_dict = defaultdict(list)
        #maps from msg id to MulticastMessage
        self.msg_dict = {}
        self.id_count = 0
        #maps from message id to number of messages in msg group
        self.group_size_dict = defaultdict(int)
        #target is the callable object to be invoked in a separate thread on start()
        self.listener = threading.Thread(target=self.listen)
        self.listener.daemon = True
        self.listener.start()

    #so far duplicates are the only possible issue 
    def listen(self):
        while True:
            if self.reliable_channel.can_recv():
                addr, msg = self.reliable_channel.recv()
                #MulticastMessage(data='b', msg_id=0)
                if isinstance(msg, MulticastMessage):
                    #simply add to list. will be processed later when seq number is received 
                    #check whether the addr ms combo is in undeliverable list before adding it
                    if (addr,msg) not in self.undeliverable:  
                      self.undeliverable.append((addr, msg))
                    suffixed_priority = int(str(self.seq + 1) + str(self.from_id))
                    #keep the same msg id as the multicastmessage. 
                    proposal = Proposal(suffixed_priority, msg.msg_id, self.addr)
                    #send proposal back to initiator
                    self.reliable_channel.unicast(proposal, addr)
                elif isinstance(msg, Proposal):
                    #means that someone responded. put it on the list of responses for the id
                    self.response_dict[msg.msg_id].append(msg)
                    #print self.response_dict[msg.msg_id]
                    # need to account for number of processes in group which was initialized on the multicast
                    if len(self.response_dict[msg.msg_id]) == self.group_size_dict[msg.msg_id]:
                        #get all the proposal of processes that you sent the message to
                        list_of_responses = self.response_dict[msg.msg_id]
                        #the final priority that you will send back will be the max of the seq
                        final_priority = max(list_of_responses, key=lambda x: x.seq)
                        #print "final_priority = " + str(final_priority) + "in " + str(list_of_responses) 
                        #MarkedMessage(seq=14, data=MulticastMessage(data='b', msg_id=0), msg_id=0, addr=('192.168.1.116', 40062))
                        final_msg = MarkedMessage(final_priority.seq,self.msg_dict[msg.msg_id],msg.msg_id,self.addr) 
                        #recreate the group of processes to send a final priority
                        group = [ proposal.addr for proposal in list_of_responses ]
                        #print str(self.from_id) + " " + str(self.msg_dict[msg.msg_id]) +  " TO GROUP" + str(group)
                        self.final_multicast(final_msg, group, self.from_id)
                elif isinstance(msg, MarkedMessage):
                    #means you received the final priority
                    #keep track of the latest sequence number heard so far
                    self.seq = max(msg.seq,self.seq)
                    #remove from undeliverable list and put in deliverable priority queue
                    self.undeliverable.remove((addr,msg.data))
                    self.delivered.put((msg.seq,msg))
   
    def can_recv(self):
        return not self.delivered.empty()

    def recv(self):
        #MarkedMessage(seq=14, data=MulticastMessage(data='d', msg_id=0), msg_id=0, addr=('192.168.1.116', 40061))
        msg = self.delivered.get()
        return msg 

    #obj is one of [A,B,C...E]
    def multicast(self, obj, group, from_id):
        #verified that group size is correct. need to create a mapping between msg_id and group size
        self.group_size_dict[self.id_count] = len(group)
        #msg id starts at 0
        msg = MulticastMessage(obj,self.id_count)
        #store the message. will contain every message you send
        self.msg_dict[self.id_count] = msg 
        for addr in group:
            self.reliable_channel.unicast(msg, addr)
        self.id_count += 1


    def final_multicast(self, msg, group, from_id):
        for addr in group:
            self.reliable_channel.unicast(msg, addr)
