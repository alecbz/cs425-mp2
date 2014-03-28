import random
import threading
import time
import pickle


class UnreliableChannel:

    '''A very thin wrapper around a UDP socket that supports sending of
    python objects via pickle serialization, as well as "simulated"
    latency/lossiness in the form of an explicit average delay time and
    message drop rate.

    UnreliableChannel is also thread-safe: it ensures its socket is not
    used concurrently for send()ing and recv()ing.'''

    def __init__(self, sock, drop_rate, delay_avg):
        self.sock = sock
        self.drop_rate = drop_rate
        self.delay_avg = delay_avg

        self.send_lock = threading.Lock()
        self.recv_lock = threading.Lock()

    def actual_unicast(self, obj, addr):
        if random.random() > self.drop_rate:
            time.sleep(random.uniform(0, 2 * self.delay_avg))
            with self.send_lock:
                self.sock.sendto(pickle.dumps(obj), addr)

    def unicast(self, obj, addr):
        t = threading.Thread(target=self.actual_unicast, args=(obj, addr))
        t.start()

    def recv(self):
        with self.recv_lock:
            data, addr = self.sock.recvfrom(1024)
        msg = pickle.loads(data)
        return msg, addr
