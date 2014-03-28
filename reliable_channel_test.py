import unittest
import random
import time
import threading

from Queue import Queue

from reliable_channel import ReliableChannel, Message, Ack
from unreliable_channel import UnreliableChannel


class FakeUnreliableChannel:

    def __init__(self, drop_rate=0, delay_avg=0.01):
        self.q = Queue()
        self.drop_rate = drop_rate
        self.delay_avg = delay_avg

    def simulate_recv(self, msg, addr):
        time.sleep(random.uniform(0, 2 * self.delay_avg))
        if random.random() > self.drop_rate:
            self.q.put((msg, addr))

    def unicast(self, obj, addr):
        if isinstance(obj, Message):
            t = threading.Thread(
                target=self.simulate_recv, args=(Ack(obj.seq), addr))
            t.daemon = True
            t.start()

    def recv(self):
        return self.q.get()


class ReliableChannelTest(unittest.TestCase):

    def setUp(self):
        self.unreliable_channel = FakeUnreliableChannel()
        self.ch = ReliableChannel(self.unreliable_channel)

    def test_unicast_no_failure(self):
        obj = ('A', 'test', 'obj')
        addr = ('0.0.0.0', 0)

        t = threading.Thread(target=self.ch.unicast, args=(obj, addr))
        t.start()
        t.join(1)

        self.assertFalse(t.is_alive())

if __name__ == '__main__':
    unittest.main()
