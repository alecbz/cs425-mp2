# CS 425 MP2

Code for Alec Benzer and Vignesh Raja's solution to MP2

## Running

Run `./mp2.py --help` to see usage. An example execution is:

    ./mp2.py --delay 0.001 --drop_rate 0.1 config.json

This reads from the `config.json` file to get certain configurable variables. A sample `config.json` file is shown here:

    {
      "num_processes": 6,
      "ordering": "causal"
    }

With this `config.json`, the preceding `./mp2.py` invocation will launch 6 local processes that communicate to each other via causally ordered multicasts. To use totally ordered multicasts instead, one can specify `"ordering": "total"` in the config file.


## Description of Algorithm

We build our multicasts off of a reliable unicast which is based on unreliable unicast. Within UnreliableChannel, we have a thin wrapper around a UDP socket that supports 
sending python objects through pickle serialization. In addition, UnreliableChannel, simulates latency/lossiness by selecting a sleep delay on unicasts and dropping a portion of messages. 

ReliableChannel is built on top of UnreliableChannel and uses acknowledgement messages to confirm that a message has been successfully received by a recipient. 
In order to keep track of acknowledgements received, we identify a message by the sender's address and a sequence number associated with each message. We use a set to store all 
(addr, seq) combinations received so far. On receiving an acknowledgement, the process stops repeatedly unicasting the message to the recipient.

The two ordering schemes we implemented are causal and total. CausalMulticastChannel maintains a dictionary that maps from message recipient groups to vector timestamps. On receipt of a message with a particular vector, we add the message to the delivered queue based on whether it satisfies the causality requirements described in the causal ordering algorithm. 

TotalOrderingChannel uses 3 different types of messages for representing the different stages of the ISIS algorithm: initially sending a message to a group of processes (MulticastMessage),
sending a proposed priority value back to a sender after receiving a message (Proposal), and sending a final priority value to the group based on the proposals received (MarkedMessage). Each process maintains
a Priority Dictionary which maps from Tuples of the form (sender address, MulticastMessage) to priority values. The Tuple with the lowest priority value will only be delivered if its deliverable
tag is set to True. If it isn't, then no message will be delivered.
