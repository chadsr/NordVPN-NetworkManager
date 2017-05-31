#!/usr/bin/env python3
import configparser
import argparse
from urllib import error, request
import os
import subprocess
from io import BytesIO
from zipfile import ZipFile
import logging
import pickle
import socket
import sys

# TODO: Terminate script/wait cleanly if network connection goes down

TIMEOUT = 30

DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = DIR+'/data/'
CONFIG_PATH = DIR+'/settings.conf'
LIST_PATH = DIR+'/.list'
NORD_URL = "https://nordvpn.com/api/files/zip"


class ConfigHandler(object):
    def __init__(self):
        self.data = configparser.ConfigParser()

        # Generate default config
        self.data['General'] = {}
        self.data['General']['country-blacklist'] = '# simply write country codes separated by spaces e.g. "country-blacklist = us ca"'
        self.data['General']['country-whitelist'] = '# simply write country codes separated by spaces e.g. "country-whitelist = us ca" If this is non-empty, the blacklist is ignored'

        self.data['Credentials'] = {}
        self.data['Credentials']['username'] = ''
        self.data['Credentials']['password'] = ''

    def save(self, path):
        with open(path, 'w') as config_file:
            self.data.write(config_file)

    def load(self, path):
        self.data.read(path)

    def get_username(self):
        return self.data['Credentials']['username']

    def get_password(self):
        return self.data['Credentials']['password']

    def get_blacklist(self):
        return self.data['General']['country-blacklist'].split(' ')

    def get_whitelist(self):
        return self.data['General']['country-whitelist'].split(' ')


class Importer(object):
    def __init__(self):
        if os.getuid() != 0:
            raise NotSudo("This script needs to be run as sudo (due to editing system-connections)")

        logging.basicConfig(format='[%(levelname)s]: %(message)s', level=logging.INFO, stream=sys.stdout)

        self.config = ConfigHandler()

        self.black_list = []
        self.white_list = []
        if os.path.isfile(CONFIG_PATH):
            self.config.load(CONFIG_PATH)
            self.black_list = self.config.get_blacklist()
            self.white_list = self.config.get_whitelist()
        else:
            self.config.save(CONFIG_PATH)

        self.active_list = []
        if os.path.isfile(LIST_PATH):
            self.active_list = self.load_active_list(LIST_PATH)

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--sync", help="Synchronise any new connections, whilst preserving existing connections. (default)", action="store_true")
        self.parser.add_argument("--purge", help="Remove all active connections.", action="store_true")
        self.parser.add_argument("--clean-sync", help="Remove all active connections and synchronise.", action="store_true")
        self.parser.add_argument("--auto-connect", help="Configure NetworkManager to always auto-connect to the lowest latency server. Specify a country code, or 'all' for all servers", type=str)

    def start(self):
        updated = False

        try:
            args = self.parser.parse_args()
        except:
            self.parser.print_help()
            self.parser.exit(1)

        self.disconnect_active_vpn()  # Disconnect active VPNs, so we get a more reliable benchmark

        if args.sync:
            updated = self.sync_imports(NORD_URL)
        elif args.purge:
            self.purge_active_connections()
        elif args.clean_sync:
            updated = self.purge_active_connections()
            updated = self.sync_imports(NORD_URL)
        else:
            updated = self.sync_imports(NORD_URL)

        if args.auto_connect:
            if self.active_list:
                if args.auto_connect == "all":
                    updated = self.select_auto_connect()
                else:
                    updated = self.select_auto_connect(args.auto_connect)
            else:
                logging.error("No servers active. Please sync before trying to set up an auto-connect.")

        if updated:
            self.restart_networkmanager()

    def restart_networkmanager(self):
        logging.info("Attempting to restart NetworkManager.")
        try:
            subprocess.run("systemctl restart NetworkManager.service", shell=True, check=True)
            logging.info("NetworkManager restarted successfully!")
        except Exception as ex:
            logging.error(ex)

    def add_credentials(self, filename):
        try:
            config = configparser.ConfigParser()
            path = "/etc/NetworkManager/system-connections/"+filename

            if os.path.isfile(path):
                config.read(path)
            elif os.path.isfile(path+'_'):
                path = path+'_'
                config.read(path)
            else:
                logging.info("VPN file not found! %s", path)
                return

            config['vpn']['password-flags'] = "0"
            config['vpn']['username'] = self.config.get_username()
            config['vpn-secrets'] = {}
            config['vpn-secrets']['password'] = self.config.get_password()

            with open(path, 'w') as config_file:
                config.write(config_file)
        except Exception as e:
            print(e)

    def import_ovpn(self, filename):
        try:
            output = subprocess.run(['nmcli', 'connection', 'import', 'type', 'openvpn', 'file', DATA_DIR+filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
            logging.info("%s", output)
            split_name = os.path.splitext(filename)
            self.add_credentials(split_name[0])
            self.active_list.append(split_name[0])
            self.save_active_list(self.active_list, LIST_PATH)
        except Exception as ex:
            logging.error(ex)

    def remove_connection(self, connection_name):
        try:
            output = subprocess.run(['nmcli', 'connection', 'delete', connection_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
            logging.info("%s", output)
        except Exception as ex:
            logging.error(ex)

    def disconnect_active_vpn(self):
        logging.info('Attempting to disconnect any active VPN connections.')

        try:
            lines = subprocess.run(['nmcli', 'connection', 'show', '--active'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').split('\n')
            labels = lines[0].split()

            for line in lines[1:]:
                if line:
                    elements = line.split()
                    connection = {}
                    for i, element in enumerate(elements):
                        connection[labels[i]] = element

                    if connection['TYPE'] == "vpn" and connection['NAME'] in self.active_list:  # Only deactivate VPNs managed by this tool. Preserve any not in the active list
                        output = subprocess.run(['nmcli', 'connection', 'down', connection['UUID']], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
                        logging.info("%s", output)

        except Exception as ex:
            logging.error(ex)

    def select_auto_connect(self, selected_country=False, acceptable_rtt=5.0):
        best_connection = None
        best_rtt = 999999.0

        logging.info("Searching for server with lowest latency...")

        for connection_name in self.active_list:
            if selected_country and connection_name[:2] == selected_country or not selected_country:
                config = configparser.ConfigParser()
                path = "/etc/NetworkManager/system-connections/"+connection_name

                if os.path.isfile(path):
                    config.read(path)
                elif os.path.isfile(path+'_'):
                    path = path+'_'
                    config.read(path)
                else:
                    logging.error("VPN file not found!", path)
                    return

                host = config['vpn']['remote'].split(':')[0]

                rtt = self.get_rtt(host)
                if not rtt:
                    logging.warning("%s (%s): Unable to test RTT", connection_name, host)
                elif rtt < best_rtt:
                    best_connection = connection_name
                    best_rtt = rtt
                    logging.info("%s (%s): %.2fms avg RTT [NEW BEST]", best_connection, host, best_rtt)

                    if best_rtt <= acceptable_rtt:
                        logging.info("%s (%s): RTT <= acceptable RTT (%.2f). Stopping here.", best_connection, host, acceptable_rtt)
                        break
                else:
                    logging.info("%s (%s): %.2fms avg RTT", connection_name, host, rtt)

        if best_connection:
            logging.info("Selecting %s (%s) for auto-connect.", best_connection, host)
            self.set_auto_connect(best_connection)
            return True

    def set_auto_connect(self, connection):
        auto_script = """#!/bin/bash
        if [ "$2" = "up" ]; then
            nmcli con up id """+connection+"""
        fi
        """

        path = "/etc/NetworkManager/dispatcher.d/auto_vpn"

        with open(path, "w") as auto_vpn:
            print(auto_script, file=auto_vpn)

        self.make_executable(path)

    def make_executable(self, path):
        mode = os.stat(path).st_mode
        mode |= (mode & 0o444) >> 2    # copy R bits to X
        os.chmod(path, mode)

    def get_rtt(self, host, ping_attempts=3):
        output = subprocess.run(['fping', host, '-c', str(ping_attempts)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8')
        loss = int(output.strip().split('/')[4].split('%')[0])  # percentage loss
        if loss < 100:
            avg_rtt = output.split()[-1].split('/')[1]
            return round(float(avg_rtt), 2)
        else:
            return False

    def download_configs(self, url):
        try:
            logging.info("Downloading latest configs from %s", url)
            uo = request.urlopen(url, timeout=TIMEOUT)
            zipfile = ZipFile(BytesIO(uo.read()))

            zipfile.extractall(DATA_DIR)
        except (error.URLError) as e:
            logging.error(e)

    def purge_active_connections(self):
        if self.active_list:
            logging.info("Removing all active connections...")
            for connection in self.active_list:
                self.remove_connection(connection)

            self.active_list = []
            self.save_active_list(self.active_list, LIST_PATH)

            logging.info("All active connections removed!")

            return True
        else:
            logging.info("No active connections to remove.")

    def load_active_list(self, path):
        try:
            with open(LIST_PATH, 'rb') as fp:
                itemlist = pickle.load(fp)
            return itemlist
        except Exception as ex:
            logging.error(ex)
            return None

    def save_active_list(self, itemlist, path):
        try:
            with open(LIST_PATH, 'wb') as fp:
                pickle.dump(itemlist, fp)
        except Exception as ex:
            logging.error(ex)

    def get_country_code(self, connection_name):
        # hacky
        return connection_name[:2]

    # Generic test to see if we can connect to a host successfully
    def host_reachable(self, host):
        try:
            request.urlopen(host, timeout=1)
            return True
        except request.URLError as err:
            return False

    # Opens a given .ovpn file and tests the given port to see if it's open/available
    def vpn_reachable(self, filename, timeout=2):
        protocol = ""
        host = ""
        port = ""

        with open(DATA_DIR+filename) as config:
            for line in config:
                if not line.isspace():
                    split = line.split()
                    name = split[0]
                    if name == "proto":
                        protocol = split[1]
                    elif name == "remote":
                        host = split[1]
                        port = int(split[2])

        if protocol == "tcp":
            socket_type = socket.SOCK_STREAM
        elif protocol == "udp":
            socket_type = socket.SOCK_DGRAM
        else:
            logging.warning("Protocol missing from config? Skipping %s", filename)
            return False

        s = socket.socket(socket.AF_INET, socket_type)
        try:
            s.settimeout(timeout)
            s.connect((host, port))
            s.shutdown(2)
            return True
        except Exception as ex:
            logging.warning("Skipping %s (%s): %s", filename, host, ex)
            return False

    def sync_imports(self, download_url):
        if self.host_reachable(download_url):
            self.download_configs(download_url)

            logging.info("Checking if any active connections should be removed...")
            # first check if anything needs purging from the existing connections
            purged = []
            for connection in self.active_list:
                country_code = self.get_country_code(connection)
                if (country_code in self.black_list) or (country_code not in self.white_list) or (not self.vpn_reachable(connection+'.ovpn')):
                    self.remove_connection(connection)
                    purged.append(connection)

            # Remove any purged from the active list, since we're done syncing
            for connection in purged:
                self.active_list.remove(connection)
                self.save_active_list(self.active_list, LIST_PATH)

            if purged:
                logging.info("Removed %i active connections.", len(purged))
            else:
                logging.info("No active connections to remove.")

            logging.info("Checking for new connections to import...")
            # Then begin checking for new
            new_imports = 0
            for filename in os.listdir(DATA_DIR):
                split_name = os.path.splitext(filename)
                country_code = self.get_country_code(filename)

                if (country_code in self.white_list) or (not self.white_list and country_code not in self.black_list):
                    test_success = self.vpn_reachable(filename)
                    if (test_success and (split_name[0] not in self.active_list)):  # If connection can be established and is not yet imported
                        self.import_ovpn(filename)
                        new_imports += 1

            if new_imports > 0:
                logging.info("Imported %i new configurations.", new_imports)
            else:
                logging.info("No new configurations to be imported.")

            if purged or new_imports > 0:  # If any changes have been made
                return True
        else:
            logging.warning("Could not establish a connection to %s. Please check your connectivity and try again.", download_url)
            sys.exit(1)


class NotSudo(Exception):
    pass


importer = Importer()
importer.start()
