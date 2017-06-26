from urllib import error, request
import json
from operator import itemgetter
import logging

API_ADDR = 'https://api.nordvpn.com'
TIMEOUT = 5

# Mapping of NordVPN category names to their short internal names
VPN_CATEGORIES = {
    'Standard VPN servers': 'normal',
    'P2P': 'p2p',
    'Double VPN': 'double',
    'Dedicated IP servers': 'dedicated',
    'Onion over VPN': 'onion',
    'Anti DDoS': 'ddos',
    }

logger = logging.getLogger(__name__)


def get_server_list(sort_by_load=False):
    try:
        resp = request.urlopen(API_ADDR + '/server', timeout=TIMEOUT)
        server_list = json.load(resp)

        if sort_by_load:
            return sorted(server_list, key=itemgetter('load'))
        else:
            return server_list
    except (error.URLError) or Exception as ex:
        logger.error(ex)
        return None


def get_nameservers():
    try:
        resp = request.urlopen(API_ADDR + '/dns/smart', timeout=TIMEOUT).read()
        return resp
    except (error.URLError) or Exception as ex:
        logger.error(ex)
        return None


def get_configs():
    try:
        resp = request.urlopen(API_ADDR + '/files/zipv2', timeout=TIMEOUT)
        return resp
    except (error.URLError) or Exception as ex:
        logger.error(ex)
        return None


'''
def get_server_loads():
    try:
        resp = request.urlopen(API_ADDR + '/server/stats', timeout=TIMEOUT)
        return json.load(resp)
    except (error.URLError) or Exception as ex:
        logger.error(ex)
        return None
'''
