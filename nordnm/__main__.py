#!/usr/bin/env python3

from nordnm import nordnm, __package__
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
        print("%s must be run as root! Exiting." % __package__)
        sys.exit(1)

    logging.basicConfig(format='[%(levelname)s] [%(name)s]: %(message)s', level=logging.INFO, stream=sys.stdout)
    signal.signal(signal.SIGINT, sig_clean_exit)

    nordnm.NordNM()


if __name__ == "__main__":
    main()
