import requests
from operator import itemgetter

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


def get_server_list(sort_by_load=False, sort_by_country=False):
    try:
        resp = requests.get(API_ADDR + '/server', timeout=TIMEOUT)
        if resp.status_code == requests.codes.ok:
            server_list = resp.json()

            if sort_by_load:
                return sorted(server_list, key=itemgetter('load'))
            elif sort_by_country:
                return sorted(server_list, key=itemgetter('country'))
            else:
                return server_list
        else:
            return None
    except Exception as ex:
        return None


def get_nameservers():
    return ['162.242.211.137', '78.46.223.24']

    # Apparently this is not the standard DNS endpoint, but something to do with 'smart-play' and no longer provides valid nameservers
    # so for now we will just return a static list...
    """
    try:
        resp = requests.get(API_ADDR + '/dns/smart', headers=HEADERS, timeout=TIMEOUT)
        return resp.json()
    except Exception as ex:
        return None
    """


def get_configs():
    try:
        resp = requests.get(API_ADDR + '/files/zipv2', timeout=TIMEOUT)
        if resp.status_code == requests.codes.ok:
            return resp.content
        else:
            return None
    except Exception as ex:
        return None
