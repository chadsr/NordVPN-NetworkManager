import utils

import subprocess
import shutil
import os
import configparser
import logging

AUTO_CONNECT_PATH = "/etc/NetworkManager/dispatcher.d/auto_vpn"

logger = logging.getLogger(__name__)


def restart():
    logger.info("Attempting to restart NetworkManager.")
    try:
        subprocess.run("systemctl restart NetworkManager.service", shell=True, check=True)
        logger.info("NetworkManager restarted successfully!")
        return True
    except Exception as ex:
        logger.error(ex)
        return False


def get_interfaces(wifi=True, ethernet=True):
    lines = subprocess.run(['nmcli', 'dev', 'status'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').split('\n')
    labels = lines[0].split()

    interfaces = []
    for line in lines[1:]:
        if line:
            elements = line.split()
            interface = {}
            for i, element in enumerate(elements):
                interface[labels[i]] = element

            if (wifi and interface['TYPE'] == 'wifi') or (ethernet and interface['TYPE'] == 'ethernet'):
                interfaces.append(interface['DEVICE'])

    return interfaces


def set_auto_connect(connection):
    interfaces = '|'.join(get_interfaces())
    print(interfaces)

    auto_script = """#!/bin/bash
    if [[ "$1" =~ """+interfaces+""" ]] && ["$2" = "up"]; then
        nmcli con up id '"""+connection+"""'
    fi"""

    with open(AUTO_CONNECT_PATH, "w") as auto_vpn:
        print(auto_script, file=auto_vpn)

    utils.make_executable(AUTO_CONNECT_PATH)


def remove_autoconnect():
    try:
        os.remove(AUTO_CONNECT_PATH)
        return True
    except OSError:
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

        output = subprocess.run(['nmcli', 'connection', 'import', 'type', 'openvpn', 'file', temp_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
        logger.info("%s", output)
        os.remove(temp_path)

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
    except Exception as ex:
        logger.error(ex)
        return False


def remove_connection(connection_name):
    try:
        output = subprocess.run(['nmcli', 'connection', 'delete', connection_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
        logger.info("%s", output)
        return True
    except Exception as ex:
        logger.error(ex)
        return False


def disconnect_active_vpn(active_list):
    logger.info('Attempting to disconnect any active VPN connections.')

    try:
        lines = subprocess.run(['nmcli', 'connection', 'show', '--active'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').split('\n')
        labels = lines[0].split()

        for line in lines[1:]:
            if line:
                elements = line.split()
                connection = {}
                for i, element in enumerate(elements):
                    connection[labels[i]] = element

                if connection['TYPE'] == "vpn" and connection['NAME'] in active_list:  # Only deactivate VPNs managed by this tool. Preserve any not in the active list
                    output = subprocess.run(['nmcli', 'connection', 'down', connection['UUID']], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
                    logger.info("%s", output)

        return True

    except Exception as ex:
        logger.error(ex)
        return False
