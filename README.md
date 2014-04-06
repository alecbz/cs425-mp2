# CS 425 MP2

Code for Alec Benzer and Vignesh Rajas's solution to MP2

## Running

## Description of Algorithm

We build our B-Multicast off of reliable unicast which is based on unreliable unicast. Within UnreliableChannel, we have a thin wrapper around a UDP socket that supports 
sending python objects through pickle serialization. In addition, UnreliableChannel, simulates latency/lossiness by uniformly selecting a sleep delay on unicasts; this delay
is calculated according to an average delay time and message drop rate provided by the user.

ReliableChannel is constructed with UnreliableChannel as a parameter and uses acknowledgement messages to confirm that a message has been successfully received by a recipient. 
In order to keep track of acknowledgements received, we identify a message by the sender's address and a sequence number computed by the sender. We use a set to store all 
(addr, seq) combinations received so far. On receiving an acknowledgement, the process stops repeatedly unicasting the message to the recipient.

The two ordering schemes we implemented are Causal and Total. CausalMulticastChannel maintains a dictionary that maps from message recipient groups to lists; these lists are 
initialized to length equal to the number of processes and all elements are set to 0. On receiving a message with a specified vector, we add the message to the delivered Queue based 
on whether it satisfies the causality and fifo requirements described in the Causal Ordering algorithm. 

TotalOrderingChannel uses 3 different types of messages for representing the different stages of the Total Ordering algorithm: initially sending a message to a group of processes (MulticastMessage),
sending a proposed priority value back to a sender after receiving a message (Proposal), and sending a final priority value to the group based on the proposals received (MarkedMessage). Each process maintains
a Priority Dictionary which maps from Tuples of the form (sender address, MulticastMessage) to priority values. The Tuple with the lowest priority value will only be delivered if its deliverable
tag is set to True. If it isn't, then no message will be delivered.
