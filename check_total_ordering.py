import re
from collections import namedtuple

MarkedMessage = namedtuple('MarkedMessage', ['seq', 'data', 'msg_id', 'addr'])

def check_logs():
    log_files = ["40060.log", "40061.log", "40062.log", "40063.log", "40064.log"]
    for lf in log_files:
        print "Log File: " + lf
        log_file = open(lf)
        pattern = re.compile("\'MarkedMessage.+\'") 
        for line in log_file:
            match = pattern.search(line)
            if match:
                print match.group()
        print ""

def main():
    check_logs()

if __name__ == "__main__":
    main()
