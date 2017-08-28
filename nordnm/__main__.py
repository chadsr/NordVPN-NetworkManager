#!/usr/bin/env python3

from nordnm import NordNM
import sys
import logging
import os


def main(argv):
    NordNM()


if __name__ == "__main__":
    if os.getuid() != 0:
        print("This script must be run as root! Exiting.")
        sys.exit(1)

    logging.basicConfig(format='[%(levelname)s] [%(name)s]: %(message)s', level=logging.INFO, stream=sys.stdout)
    main(sys.argv)
