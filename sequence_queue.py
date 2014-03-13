import threading
from heapq import *
from operator import itemgetter


class SequenceQueue:

    '''Manages a queue of objects with associated sequences numbers.
    Sequences numbers are expected to be integers >= 1. Objects with
    various sequence numbers can be pushed onto the queue, and popping
    off the queue will return the object with the lowest non-yet-popped
    sequence number, or else wait until that object is available.

    Eg:

    q = SequenceQueue()
    # a bunch of q.push() calls
    assert q.pop().seq == 1
    assert q.pop().seq == 2
    assert q.pop().seq == 3'''

    def __init__(self, key=itemgetter(0)):
        self.key = key

        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

        self.heap = []

        self.expecting = 1
        self.seen = set()

    def push(self, obj):
        "Push a new object onto the queue."
        with self.lock:
            if self.key(obj) in self.seen:
                return
            self.seen.add(self.key(obj))
            heappush(self.heap, obj)
            if self.key(obj) == self.expecting:
                self.cond.notify()

    def _wait_for_next(self, timeout=None):
        '''Wait until the object we are expecting next is present in the
        queue. Returns true if the expected object is found, or false if
        it did not arrive within the given timeout.
        
        Expects that self.lock is held.'''
        if not (self.heap and self.key(self.heap[0]) == self.expecting):
            self.cond.wait(timeout)
        if not self.heap or self.key(self.heap[0]) != self.expecting:
            return False
        return True

    def pop(self, timeout=None):
        with self.lock:
            if self._wait_for_next(timeout):
                self.expecting += 1
                return heappop(self.heap)

    def peek(self, timeout=None):
        with self.lock:
            if self._wait_for_next(timeout):
                return self.heap[0]

    def __len__(self):
        return len(self.heap)
