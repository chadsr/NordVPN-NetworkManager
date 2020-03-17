import requests
from operator import itemgetter

API_ADDR = 'https://api.nordvpn.com'
OVPN_ADDR = 'https://downloads.nordcdn.com/configs/archives/servers/ovpn.zip'
TIMEOUT = 5

# 2xx Status codes
STATUS_OK = 200
STATUS_CREATED = 201
STATUS_SUCCESS = [
    STATUS_OK,
    STATUS_CREATED,
]

# 3xx Status codes
STATUS_MOVED_PERM = 301
STATUS_FOUND = 302
STATUS_MOVED_TEMP = 307
STATUS_REDIRECT_PERM = 308
STATUS_REDIRECT = [
    STATUS_MOVED_PERM,
    STATUS_FOUND,
    STATUS_MOVED_TEMP,
    STATUS_REDIRECT_PERM,
]

# Mapping of NordVPN category names to their short internal names
VPN_CATEGORIES = {
    'Standard VPN servers': 'normal',
    'P2P': 'p2p',
    'Double VPN': 'double',
    'Dedicated IP': 'dedicated',
    'Onion Over VPN': 'onion',
    'Anti DDoS': 'ddos',
}


def get_server_list(sort_by_load=False, sort_by_country=False):
    try:
        resp = requests.get(API_ADDR + '/server', timeout=TIMEOUT)
        if resp.status_code in STATUS_SUCCESS:
            server_list = resp.json()

            if sort_by_load:
                return sorted(server_list, key=itemgetter('load'))
            elif sort_by_country:
                return sorted(server_list, key=itemgetter('country'))
            else:
                return server_list
        else:
            return None
    except Exception:
        return None


def get_configs(etag=None):
    try:
        head = requests.head(OVPN_ADDR, timeout=TIMEOUT)

        # Follow the redirect if there is one
        if head.status_code in STATUS_REDIRECT:
            redirect_url = head.headers['Location']
            head = requests.head(redirect_url, timeout=TIMEOUT)

        if head.status_code in STATUS_SUCCESS:
            header_etag = head.headers['etag']

            if header_etag != etag:
                resp = requests.get(OVPN_ADDR, timeout=TIMEOUT)
                if resp.status_code in STATUS_SUCCESS:
                    return (resp.content, header_etag)
            else:
                return (None, None)
        else:
            return False
    except Exception as ex:
        print(ex)
        return False


def get_user_token(email, password):
    """
    Returns
    {
        "user_id": 1234567,
        "token": "some_token",
        "expires_at": "date",
        "updated_at": "date",
        "created_at": "date",
        "id": 1234567890,
        "renew_token": "some_renew_token"
    }
    """

    json_data = {'username': email, 'password': password}

    try:
        resp = requests.post(API_ADDR + '/v1/users/tokens',
                             json=json_data,
                             timeout=TIMEOUT)
        if resp.status_code in STATUS_SUCCESS:
            return resp.content
        else:
            return None
    except Exception:
        return None


def verify_user_credentials(email, password):
    token = get_user_token(email, password)

    if token is None:
        return False

    return True
