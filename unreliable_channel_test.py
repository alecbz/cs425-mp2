import unittest
from collections import deque
from mock import patch

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
        self.sock = FakeSocket()

    def test_unicat_no_drop_or_delay(self):
        ch = UnreliableChannel(self.sock, 0, 0)
        ch.unicast(self.obj, self.addr)

        obj, addr = ch.recv()

        self.assertEqual(obj, self.obj)
        self.assertEqual(addr, self.addr)

    def test_unicat_delay_but_no_drop(self):
        ch = UnreliableChannel(self.sock, 0, 0.01)
        ch.unicast(self.obj, self.addr)

        obj, addr = ch.recv()

        self.assertEqual(obj, self.obj)
        self.assertEqual(addr, self.addr)

    def test_unicast_drop_and_delay(self):
        ch = UnreliableChannel(self.sock, 0.5, 0.2)

        with patch('random.random', return_value=0.75):  # message will go through
            ch.unicast(self.obj, self.addr)
        obj, addr = ch.recv()
        self.assertEqual(obj, self.obj)
        self.assertEqual(addr, self.addr)

        with patch('random.random', return_value=0.25):
            ch.unicast(self.obj, self.addr)
        self.assertEqual(len(self.sock.messages), 0)


if __name__ == '__main__':
    unittest.main()
