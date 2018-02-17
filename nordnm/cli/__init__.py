import os
import sys

from nordnm import log


def ensure_sudo(func):
    try:
        int(os.getenv('SUDO_UID'))
        int(os.getenv('SUDO_GID'))
    except TypeError:
        log.error('This command requires sudo!')
        sys.exit(1)
    return func
