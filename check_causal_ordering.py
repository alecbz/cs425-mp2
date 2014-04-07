#!/usr/bin/python
import pickle
from glob import glob
from mp2 import Address

def vector_lt(v1, v2):
    return all(a <= b for (a, b) in zip(v1, v2)) and any(a != b for (a, b) in zip(v1, v2))


def main():
    logs = [open(f, 'r') for f in glob('*.binlog')]
    messages = []
    for log in logs:
        msgs = []
        while True:
            try:
                addr, vec = pickle.load(log)
                msgs.append(vec)
            except EOFError:
                break
        messages.append(msgs)

    for msgs in messages:
        for i in range(len(msgs) - 1):
            if vector_lt(msgs[i + 1], msgs[i]):
                print False
                return 1
    print True


if __name__ == "__main__":
    main()
