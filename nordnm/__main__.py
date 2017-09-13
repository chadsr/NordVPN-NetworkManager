#!/usr/bin/env python3

from nordnm import nordnm
import sys
import logging
import os


def main():
    if os.getuid() != 0:
        print("This script must be run as root! Exiting.")
        sys.exit(1)

    logging.basicConfig(format='[%(levelname)s] [%(name)s]: %(message)s', level=logging.INFO, stream=sys.stdout)

    nordnm.NordNM()


if __name__ == "__main__":
    main()
