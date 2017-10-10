from nordnm import utils

import subprocess
import shutil
import os
import configparser
import logging

AUTO_CONNECT_PATH = "/etc/NetworkManager/dispatcher.d/auto_vpn"
KILLSWITCH_PATH = "/etc/NetworkManager/dispatcher.d/killswitch_vpn"


logger = logging.getLogger(__name__)


def restart():
    try:
        output = subprocess.run(['systemctl', 'restart', 'NetworkManager.service'])
        output.check_returncode()
        logger.info("NetworkManager restarted successfully!")
        return True

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False

    except Exception as ex:
        logger.error(ex)
        return False


def get_vpn_connections():
    try:
        output = subprocess.run(['nmcli', '--mode', 'tabular', '--terse', '--fields', 'TYPE,NAME', 'connection', 'show'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()

        lines = output.stdout.decode('utf-8').split('\n')

        vpn_connections = []
        for line in lines:
            if line:
                elements = line.strip().split(':')

                if (elements[0] == 'vpn'):
                    vpn_connections.append(elements[1])

        return vpn_connections

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False


def get_interfaces(wifi=True, ethernet=True):
    try:
        output = subprocess.run(['nmcli', '--mode', 'tabular', '--terse', '--fields', 'TYPE,DEVICE', 'device', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()

        lines = output.stdout.decode('utf-8').split('\n')

        interfaces = []
        for line in lines:
            if line:
                elements = line.strip().split(':')

                if (wifi and elements[0] == 'wifi') or (ethernet and elements[0] == 'ethernet'):
                    interfaces.append(elements[1])

        return interfaces

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False

    except Exception as ex:
        logger.error(ex)
        return False


def remove_killswitch(persistence_path):
    try:
        os.remove(KILLSWITCH_PATH)
        os.remove(persistence_path)
        return True
    except FileNotFoundError:
        return True  # Return true if the file was not found, since it's removed
    except Exception:
        return False


def set_killswitch(persistence_path):
    killswitch_script = """#!/bin/sh

PERSISTENCE_FILE=""" + persistence_path + """

case $2 in
    vpn-up)
        nmcli -f type,device connection | awk '$1~/^vpn$/ && $2~/[^\-][^\-]/ { print $2; }' > "${PERSISTENCE_FILE}"
    ;;
    vpn-down)
        echo "${PERSISTENCE_FILE}"
        xargs -n 1 -a "${PERSISTENCE_FILE}" nmcli device disconnect
    ;;
esac"""

    with open(KILLSWITCH_PATH, "w") as killswitch_vpn:
        print(killswitch_script, file=killswitch_vpn)

    utils.make_executable(KILLSWITCH_PATH)

    return True


def set_auto_connect(connection):
    interfaces = get_interfaces()

    if interfaces:
        interface_string = '|'.join(interfaces)

        auto_script = """#!/bin/sh
        if [[ "$1" =~ """ + interface_string + """ ]] && [[ "$2" =~ up|connectivity-change ]]; then
            nmcli con up id '""" + connection + """'
        fi"""

        with open(AUTO_CONNECT_PATH, "w") as auto_vpn:
            print(auto_script, file=auto_vpn)

        utils.make_executable(AUTO_CONNECT_PATH)

        return True


def remove_autoconnect():
    try:
        os.remove(AUTO_CONNECT_PATH)
        return True
    except FileNotFoundError:
        return True  # Return true if the file was not found, since it's removed
    except Exception:
        return False


def get_connection_config(connection_name):
    try:
        config = configparser.ConfigParser()
        path = "/etc/NetworkManager/system-connections/" + connection_name

        if os.path.isfile(path):
            config.read(path)
            return config
        else:
            logger.info("VPN config file not found! %s", path)
            return False
    except Exception as ex:
        logger.error(ex)
        return False


def save_connection_config(connection_name, config):
    try:
        path = "/etc/NetworkManager/system-connections/" + connection_name

        with open(path, 'w') as config_file:
            config.write(config_file)
        return True
    except Exception as ex:
        logger.error(ex)
        return False


def disable_ipv6(config):
    config['ipv6']['method'] = 'ignore'
    return config


def set_dns_nameservers(config, dns_list):
    dns_string = ';'.join(map(str, dns_list))

    config['ipv4']['dns'] = dns_string
    config['ipv4']['ignore-auto-dns'] = 'true'

    return config


def add_connection_credentials(config, username, password):
    config['vpn']['password-flags'] = "0"
    config['vpn']['username'] = username
    config['vpn-secrets'] = {}
    config['vpn-secrets']['password'] = password

    return config


def import_connection(file_path, connection_name, username=None, password=None, dns_list=None, ipv6=False):
    try:
        # Create a temporary config with the new name, for importing (and delete afterwards)
        temp_path = os.path.join(os.path.dirname(file_path), connection_name + '.ovpn')
        shutil.copy(file_path, temp_path)

        output = subprocess.run(['nmcli', 'connection', 'import', 'type', 'openvpn', 'file', temp_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.remove(temp_path)
        output.check_returncode()

        config = get_connection_config(connection_name)
        if config:
            if username and password:
                config = add_connection_credentials(config, username, password)

            if dns_list:
                config = set_dns_nameservers(config, dns_list)

            if not ipv6:
                config = disable_ipv6(config)

            save_connection_config(connection_name, config)
        else:
            return False

        return True

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False

    except Exception as ex:
        logger.error(ex)
        return False


def remove_connection(connection_name):
    try:
        output = subprocess.run(['nmcli', 'connection', 'delete', connection_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()

        return True

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False

    except Exception as ex:
        logger.error(ex)
        return False


def disconnect_active_vpn(active_servers):
    disabled = False  # Flag for checking if a VPN was disconnected

    try:
        output = subprocess.run(['nmcli', '--mode', 'tabular', '--terse', '--fields', 'TYPE,NAME,UUID', 'connection', 'show', '--active'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()
        lines = output.stdout.decode('utf-8').split('\n')

        for line in lines:
            if line:
                elements = line.strip().split(':')

                if elements[0] == "vpn":  # Only deactivate VPNs managed by this tool. Preserve any not in the active list
                    for server in active_servers.values():
                        if elements[1] == server['name']:
                            output = subprocess.run(['nmcli', 'connection', 'down', elements[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            output.check_returncode()
                            disabled = True

        return disabled

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False

    except Exception as ex:
        logger.error(ex)
        return False
