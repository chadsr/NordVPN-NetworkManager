from nordnm import utils

import subprocess
import shutil
import os
import configparser
import logging

AUTO_CONNECT_PATH = "/etc/NetworkManager/dispatcher.d/auto_vpn"
KILLSWITCH_PATH = "/etc/NetworkManager/dispatcher.d/killswitch_vpn"

logger = logging.getLogger(__name__)


class ConnectionConfig(object):
    def __init__(self, connection_name):
        self.config = configparser.ConfigParser(interpolation=None)
        self.path = os.path.join("/etc/NetworkManager/system-connections/", connection_name)

        try:
            if os.path.isfile(self.path):
                self.config.read(self.path)
            else:
                logger.error("VPN config file not found! (%s)", self.path)
                self.path = None

        except Exception as ex:
            logger.error(ex)
            self.path = None

    def save(self):
        try:
            if self.path:
                with open(self.path, 'w') as config_file:
                    self.config.write(config_file)

                return True
            else:
                logger.error("Could not save VPN Config. Invalid path.")
                return False

        except Exception as ex:
            logger.error(ex)
            return False

    def disable_ipv6(self):
        self.config['ipv6']['method'] = 'ignore'

    def set_dns_nameservers(self, dns_list):
        dns_string = ';'.join(map(str, dns_list))

        self.config['ipv4']['dns'] = dns_string
        self.config['ipv4']['ignore-auto-dns'] = 'true'

    def set_user(self, user):
        self.config['connection']['permissions'] = "user:" + user + ":;"

    def set_credentials(self, username, password):
        self.config['vpn']['password-flags'] = "0"
        self.config['vpn']['username'] = username
        self.config['vpn-secrets'] = {}
        self.config['vpn-secrets']['password'] = password


def reload_connections():
    try:
        output = subprocess.run(['nmcli', 'connection', 'reload'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()

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
        logger.info("Network kill-switch disabled.")
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_killswitch(persistence_path):
    killswitch_script = """#!/bin/bash

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

    logger.info("Network kill-switch enabled.")

    return True


def set_auto_connect(connection_name):
    interfaces = get_interfaces()

    if interfaces:
        interface_string = '|'.join(interfaces)

        auto_script = """#!/bin/bash
        if [[ "$1" =~ """ + interface_string + """ ]] && [[ "$2" =~ up|connectivity-change ]]; then
            nmcli con up id '""" + connection_name + """'
        fi"""

        with open(AUTO_CONNECT_PATH, "w") as auto_vpn:
            print(auto_script, file=auto_vpn)

        utils.make_executable(AUTO_CONNECT_PATH)

        logger.info("Auto-connect enabled for '%s'.", connection_name)

        return True


def remove_autoconnect():
    try:
        os.remove(AUTO_CONNECT_PATH)
        logger.info("Auto-connect disabled.")
        return True
    except FileNotFoundError:
        return True  # Return true if the file was not found, since it's removed
    except Exception:
        return False


def import_connection(file_path, connection_name, username=None, password=None, dns_list=None, ipv6=False):
    try:
        # Create a temporary config with the new name, for importing (and delete afterwards)
        temp_path = os.path.join(os.path.dirname(file_path), connection_name + '.ovpn')
        shutil.copy(file_path, temp_path)

        output = subprocess.run(['nmcli', 'connection', 'import', 'type', 'openvpn', 'file', temp_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.remove(temp_path)
        output.check_returncode()

        config = ConnectionConfig(connection_name)
        if config.path:  # If the config has a path, then it was loaded correctly
            if username and password:
                config.set_credentials(username, password)

            if dns_list:
                config.set_dns_nameservers(dns_list)

            if not ipv6:
                config.disable_ipv6()

            user = utils.get_current_user()
            config.set_user(user)

            config.save()
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


def enable_connection(connection_name):
    try:
        output = subprocess.run(['nmcli', 'connection', 'up', connection_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()

        return True

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False

    except Exception as ex:
        logger.error(ex)
        return False


def disable_connection(connection_name):
        try:
            output = subprocess.run(['nmcli', 'connection', 'down', connection_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output.check_returncode()

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
    disconnected_vpns = set([])

    try:
        output = subprocess.run(['nmcli', '--mode', 'tabular', '--terse', '--fields', 'TYPE,NAME,UUID', 'connection', 'show', '--active'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()
        lines = output.stdout.decode('utf-8').split('\n')

        for line in lines:
            if line:
                elements = line.strip().split(':')

                if elements[0] == "vpn":  # Only deactivate VPNs managed by this tool. Preserve any not in the active list
                    for server in active_servers.values():
                        if elements[1] == server['name'] and elements[2] not in disconnected_vpns:
                            if disable_connection(elements[2]):
                                disconnected_vpns.add(elements[2])  # Add the UUID to our set

        return bool(disconnected_vpns)

    except subprocess.CalledProcessError:
        error = utils.format_std_string(output.stderr)
        logger.error(error)
        return False

    except Exception as ex:
        logger.error(ex)
        return False
