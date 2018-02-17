__package__ = "nordnm"
__version__ = "0.3.3"
__license__ = "GNU General Public License v3 or later (GPLv3+)"

import logging
import sys

logging.basicConfig(format='[%(levelname)s] [%(name)s]: %(message)s', level=logging.INFO, stream=sys.stdout)
log = logging.getLogger('nordnm')
