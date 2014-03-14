import unittest
from collections import deque

from unreliable_channel import UnreliableChannel


class FakeSocket:

    def __init__(self):
        self.messages = deque()

    def sendto(self, data, addr):
        self.messages.append((data, addr))

    def recvfrom(self, size):
        return self.messages.popleft()


class UnreliableChannelTest(unittest.TestCase):

    def setUp(self):
        self.obj = ('A', 'test', 'object')
        self.addr = ('1.2.3.4', 80)

    def test_unicat_no_drop_or_delay(self):
        sock = FakeSocket()

        ch = UnreliableChannel(sock, 0, 0)
        ch.unicast(self.obj, self.addr)

        obj, addr = ch.recv()

        self.assertEqual(obj, self.obj)
        self.assertEqual(addr, self.addr)

    def test_unicat_delay_but_no_drop(self):
        sock = FakeSocket()

        ch = UnreliableChannel(sock, 0, 0.2)
        ch.unicast(self.obj, self.addr)

        obj, addr = ch.recv()

        self.assertEqual(obj, self.obj)
        self.assertEqual(addr, self.addr)

if __name__ == '__main__':
    unittest.main()
