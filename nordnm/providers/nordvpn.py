import requests
import json
import hashlib

from nordnm import utils
from nordnm.vpn_provider import VPNProvider


# See VPNProvider Abstract Base Class for specification
class NordVPN(VPNProvider):
    __api_endpoint__ = 'https://api.nordvpn.com'
    __ajax_endpoint__ = 'https://nordvpn.com/wp-admin/admin-ajax.php?action='
    __ovpn_endpoint = 'https://downloads.nordcdn.com/configs/archives/servers/ovpn.zip'
    __timeout__ = 5

    def get_servers(country_code, category, protocol, limit):
        # Get the official category ID based on an internal category name
        def get_category_id(category):
            def get_server_categories():
                return utils.get_json_response(NordVPN.__ajax_endpoint__ + 'servers_groups')

            available_categories = NordVPN.get_available_categories()
            category_name_long = available_categories[category]

            server_categories = get_server_categories()

            category_id = None
            for category in server_categories:
                if category['name'] == category_name_long:
                    category_id = category['id']

            return category_id

        # Get the official protocol ID based on an internal protocol name
        def get_protocol_id(protocol):
            def get_server_technologies():
                return utils.get_json_response(NordVPN.__ajax_endpoint__ + 'servers_technologies')

            available_protocols = NordVPN.get_available_protocols()
            protocol_name_long = available_protocols[protocol]
            server_technologies = get_server_technologies()

            protocol_id = None
            for protocol in server_technologies:
                if protocol['name'] == protocol_name_long:
                    protocol_id = protocol['id']

            return protocol_id

        category_id = get_category_id(category)
        protocol_id = get_protocol_id(protocol)

        if category_id and protocol_id:
            filter = {
                'flag': country_code,
                'servers_groups': [category_id],
                'servers_technologies': [protocol_id]
            }

            url = NordVPN.__ajax_endpoint__ + 'servers_recommendations&filters=' + filter + '&limit=' + str(limit)
            return utils.get_json_response(url)
        else:
            return None

    def get_nameservers(host=None):
        return ['103.86.96.100', '103.86.99.100']

    def get_configuration_files(etag=None):
        try:
            head = requests.head(NordVPN.__ovpn_endpoint, timeout=NordVPN.__timeout__)

            # Follow the redirect if there is one
            if head.status_code == requests.codes.moved:
                redirect_url = head.headers['Location']
                head = requests.head(redirect_url, timeout=NordVPN.__timeout__)

            if head.status_code == requests.codes.ok:
                header_etag = head.headers['etag']

                if header_etag != etag:
                    resp = requests.get(NordVPN.__ovpn_endpoint, timeout=NordVPN.__timeout__)
                    if resp.status_code == requests.codes.ok:
                        return (resp.content, header_etag)
                else:
                    return (None, None)
            else:
                return False
        except Exception as ex:
            print(ex)
            return False

    def get_available_countries():
        def get_server_countries():
            return utils.get_json_response(NordVPN.__ajax_endpoint__ + 'servers_countries')

    def get_available_categories():
        return {
            'normal': 'Standard VPN servers',
            'p2p': 'P2P',
            'double': 'Double VPN',
            'dedicated': 'Dedicated IP servers',
            'onion': 'Onion Over VPN',
            'ddos': 'Anti DDoS'
        }

    def get_available_protocols():
        return {
            'tcp': 'OpenVPN TCP',
            'udp': 'OpenVPN UDP'
        }

    def verify_user_credentials(username, password):
        def get_user_token(email):
            """
            Returns {"token": "some_token", "key": "some_key", "salt": "some_salt"}
            """

            try:
                resp = requests.get(NordVPN.__api_endpoint__ + '/token/token/' + email, timeout=NordVPN.__timeout__)
                if resp.status_code == requests.codes.ok:
                    return json.loads(resp.text)
                else:
                    return None
            except Exception as ex:
                return None

        def validate_user_token(token_json, password):
            token = token_json['token']
            salt = token_json['salt']
            key = token_json['key']

            password_hash = hashlib.sha512(salt.encode() + password.encode())
            final_hash = hashlib.sha512(password_hash.hexdigest().encode() + key.encode())

            try:
                resp = requests.get(NordVPN.__api_endpoint__ + '/token/verify/' + token + '/' + final_hash.hexdigest(), timeout=NordVPN.__timeout__)
                if resp.status_code == requests.codes.ok:
                    return True
                else:
                    return False
            except Exception as ex:
                return None

        token_json = get_user_token(username)
        return validate_user_token(token_json, password)
