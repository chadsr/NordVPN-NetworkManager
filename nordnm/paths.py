import os
from nordnm import utils

__username__ = utils.get_current_user()

USER_HOME = os.path.expanduser('~' + __username__)
ROOT = os.path.join(USER_HOME, '.nordnm/')
OVPN_CONFIGS = os.path.join(ROOT, 'configs/')
CONFIG_INFO = os.path.join(OVPN_CONFIGS, '.info')
SETTINGS = os.path.join(ROOT, 'settings.conf')
ACTIVE_SERVERS = os.path.join(ROOT, '.active_servers')
CREDENTIALS = os.path.join(ROOT, 'credentials.conf')
MAC_CONFIG = "/usr/lib/NetworkManager/conf.d/nordnm_mac.conf"
AUTO_CONNECT_SCRIPT = "/etc/NetworkManager/dispatcher.d/nordnm_autoconnect_" + __username__
KILLSWITCH_SCRIPT = "/etc/NetworkManager/dispatcher.d/nordnm_killswitch_" + __username__
KILLSWITCH_DATA = os.path.join(ROOT, '.killswitch')

# Legacy paths for cleanly updating. These files are removed on startup, if found
LEGACY_FILES = ["/etc/NetworkManager/dispatcher.d/auto_vpn", "/etc/NetworkManager/dispatcher.d/killswitch_vpn", "/etc/NetworkManager/dispatcher.d/nordnm_dns_" + __username__]
