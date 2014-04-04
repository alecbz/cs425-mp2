import pickle
from glob import glob


def main():
    logs = [open(f, 'r') for f in glob('*.total.binlog')]
    messages = []
    for log in logs:
        msgs = []
        while True:
            try:
                msgs.append(pickle.load(log))
            except EOFError:
                break
        messages.append(msgs)

    # truncate all lists to lenngth of the shortest one
    min_len = min(len(msgs) for msgs in messages)
    messages = [msgs[:min_len] for msgs in messages]

    first = messages[0]
    print all(msgs == first for msgs in messages)




if __name__ == "__main__":
    main()
