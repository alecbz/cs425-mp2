import unittest
from sequence_queue import *


class TestSequenceQueue(unittest.TestCase):

    def setUp(self):
        self.timeout = 0.01
        self.obj1 = (1, 'Hello')
        self.obj2 = (2, 'Goodbye')

    def test_pop_empty(self):
        q = SequenceQueue()
        self.assertIsNone(q.pop(self.timeout))

    def test_peek_empty(self):
        q = SequenceQueue()
        self.assertIsNone(q.peek(self.timeout))

    def test_pop(self):
        q = SequenceQueue()
        q.push(self.obj1)
        q.push(self.obj2)

        self.assertEqual(q.pop(self.timeout), self.obj1)
        self.assertEqual(q.pop(self.timeout), self.obj2)
        self.assertEqual(0, len(q))

    def test_peek(self):
        q = SequenceQueue()
        q.push(self.obj1)
        q.push(self.obj2)

        self.assertEqual(q.peek(self.timeout), self.obj1)
        self.assertEqual(q.peek(self.timeout), self.obj1)
        self.assertEqual(2, len(q))

    def test_missing(self):
        q = SequenceQueue()
        q.push(self.obj2)
        self.assertIsNone(q.pop(self.timeout))
        self.assertIsNone(q.peek(self.timeout))

        q.push(self.obj1)
        self.assertEqual(q.peek(self.timeout), self.obj1)
        self.assertEqual(q.pop(self.timeout), self.obj1)
        self.assertEqual(q.peek(self.timeout), self.obj2)
        self.assertEqual(q.pop(self.timeout), self.obj2)

if __name__ == '__main__':
    unittest.main()
