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
        return False
        logger.error(ex)


def set_auto_connect(connection):
    auto_script = """#!/bin/bash
    if [ "$2" = "up" ]; then
        nmcli con up id '"""+connection+"""'
    fi
    """

    with open(AUTO_CONNECT_PATH, "w") as auto_vpn:
        print(auto_script, file=auto_vpn)

    utils.make_executable(AUTO_CONNECT_PATH)


def remove_autoconnect():
    try:
        os.remove(AUTO_CONNECT_PATH)
        return True
    except OSError:
        return False


def add_connection_credentials(connection_name, username, password):
    try:
        config = configparser.ConfigParser()
        path = "/etc/NetworkManager/system-connections/" + connection_name

        if os.path.isfile(path):
            config.read(path)
        else:
            logger.info("VPN file not found! %s", path)
            return False

        config['vpn']['password-flags'] = "0"
        config['vpn']['username'] = username
        config['vpn-secrets'] = {}
        config['vpn-secrets']['password'] = password

        with open(path, 'w') as config_file:
            config.write(config_file)

        return True
    except Exception as ex:
        logger.error(ex)
        return False


def import_connection(file_path, connection_name, username=None, password=None):
    try:
        # Create a temporary config with the new name, for importing (and delete afterwards)
        temp_path = os.path.join(os.path.dirname(file_path), connection_name + '.ovpn')
        shutil.copy(file_path, temp_path)

        output = subprocess.run(['nmcli', 'connection', 'import', 'type', 'openvpn', 'file', temp_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
        #logger.info("%s", output)
        os.remove(temp_path)

        if username and password:
            add_connection_credentials(connection_name, username, password)

        return True
    except Exception as ex:
        logger.error(ex)

    return False


def remove_connection(connection_name):
    try:
        output = subprocess.run(['nmcli', 'connection', 'delete', connection_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
        #logger.info("%s", output)
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
