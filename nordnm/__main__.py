#!/usr/bin/env python3

from nordnm import nordnm, __package__
import sys
import logging
import os


def main():
    if os.getuid() != 0:
        print("%s must be run as root! Exiting." % __package__)
        sys.exit(1)

    logging.basicConfig(format='[%(levelname)s] [%(name)s]: %(message)s', level=logging.INFO, stream=sys.stdout)

    nordnm.NordNM()


if __name__ == "__main__":
    main()
