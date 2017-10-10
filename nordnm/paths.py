import os
from nordnm import utils

DIR_USERHOME = os.path.expanduser('~' + utils.get_current_user())
DIR_ROOT = os.path.join(DIR_USERHOME, '.nordnm/')
DIR_OVPN = os.path.join(DIR_ROOT, 'configs/')

SETTINGS = os.path.join(DIR_ROOT, 'settings.conf')
ACTIVE_SERVERS = os.path.join(DIR_ROOT, '.active_servers')
CREDENTIALS = os.path.join(DIR_ROOT, 'credentials.conf')
KILLSWITCH = os.path.join(DIR_ROOT, '.killswitch')
