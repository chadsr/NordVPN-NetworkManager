#!/usr/bin/env python3

from nordnm import nordnm, __package__, utils
import sys
import logging
import os
import signal

PID = os.getpid()


def sig_clean_exit(signal, frame):
    if os.getpid() == PID:
        print("\nExiting.")
    sys.exit(0)


def main():
    if os.getuid() != 0:
        print("%s must be run as root. Exiting." % __package__)
        sys.exit(1)

    # We are running with root priveledges, which is kinda scary, so lets switch to the original user until we actually need root (if there is one)
    user_uid = os.getenv("SUDO_UID")
    if user_uid:
        os.seteuid(int(user_uid))

    # Add our custom logging formatter function to handle all logging output
    formatter = utils.LoggingFormatter()
    loggingHandler = logging.StreamHandler(sys.stdout)
    loggingHandler.setFormatter(formatter)
    logging.root.addHandler(loggingHandler)
    logging.root.setLevel(logging.INFO)

    signal.signal(signal.SIGINT, sig_clean_exit)

    nordnm.NordNM()


if __name__ == "__main__":
    main()
