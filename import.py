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

TIMEOUT = 30

DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = DIR+'/data/'
CONFIG_PATH = DIR+'/settings.conf'
LIST_PATH = DIR+'/.list'


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

        logging.basicConfig(filename='output.log', level=logging.WARNING)

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

        try:
            args = self.parser.parse_args()
        except:
            self.parser.print_help()
            self.parser.exit(1)

        if args.sync:
            self.sync_imports()
        elif args.purge:
            self.purge_active_connections()
        elif args.clean_sync:
            self.purge_active_connections()
            self.sync_imports()
        else:
            self.sync_imports()

        if args.auto_connect:
            if self.active_list:
                if args.auto_connect == "all":
                    self.select_auto_connect()
                else:
                    self.select_auto_connect(args.auto_connect)
            else:
                print("No servers active. Please sync first.")

        print("Restarting NetworkManager.")
        subprocess.run("systemctl restart NetworkManager.service", shell=True, check=True)

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
                print("VPN file not found!", path)
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
        subprocess.run("nmcli connection import type openvpn file "+DATA_DIR+filename, shell=True, check=True)
        split_name = os.path.splitext(filename)
        self.add_credentials(split_name[0])
        self.active_list.append(split_name[0])
        self.save_active_list(self.active_list, LIST_PATH)

    def remove_connection(self, connection_name):
        subprocess.run("nmcli connection delete "+connection_name, shell=True, check=True)

    def select_auto_connect(self, selected_country=False):
        best_connection = None
        best_latency = 999999.0

        for connection_name in self.active_list:
            if selected_country and connection_name[:2] == selected_country:
                print("Checking latency of:", connection_name)
                config = configparser.ConfigParser()
                path = "/etc/NetworkManager/system-connections/"+connection_name

                if os.path.isfile(path):
                    config.read(path)
                elif os.path.isfile(path+'_'):
                    path = path+'_'
                    config.read(path)
                else:
                    print("VPN file not found!", path)
                    return

                host = config['vpn']['remote'].split(':')[0]

                latency = self.get_latency(host)
                if latency < best_latency:
                    best_connection = connection_name
                    best_latency = latency
                    print("Best:", best_connection, best_latency)

        if best_connection:
            self.set_auto_connect(best_connection)

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

    def get_latency(self, host):
        output = subprocess.run(['fping', host, '-c 3'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8')
        loss = int(output.strip().split('/')[4].split('%')[0])  # percentage loss
        if loss == 0:
            avg_rtt = output.split()[-1].split('/')[1]
            return float(avg_rtt)
        else:
            return 999999

    def download_configs(self, url):
        try:
            print("Downloading latest configs from", url)
            uo = request.urlopen(url, timeout=TIMEOUT)
            zipfile = ZipFile(BytesIO(uo.read()))

            zipfile.extractall(DATA_DIR)
        except (error.URLError) as e:
            print("Could not resolve", url)
            logging.error(e)

    def purge_active_connections(self):
        for connection in self.active_list:
            self.remove_connection(connection)

        self.active_list = []

    def load_active_list(self, path):
        with open(LIST_PATH, 'rb') as fp:
            itemlist = pickle.load(fp)
        return itemlist

    def save_active_list(self, itemlist, path):
        with open(LIST_PATH, 'wb') as fp:
            pickle.dump(itemlist, fp)
        print("Active list saved.")

    def get_country_code(self, connection_name):
        # hacky
        return connection_name[:2]

    def test_connection(self, filename):
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
            s.settimeout(5)
            s.connect((host, port))
            s.shutdown(2)
            return True
        except Exception as e:
            logging.warning("Could not establish a connection. Skipping %s", filename)
            return False

    def sync_imports(self):
        self.download_configs("https://nordvpn.com/api/files/zip")

        # first check if anything needs purging from the existing connections
        purged = []
        for connection in self.active_list:
            country_code = self.get_country_code(connection)
            if country_code in self.black_list or country_code not in self.white_list:
                self.remove_connection(connection)
                purged.append(connection)

        # Then begin checking for new
        for filename in os.listdir(DATA_DIR):
            split_name = os.path.splitext(filename)
            country_code = self.get_country_code(filename)

            if (country_code in self.white_list) or (not self.white_list and country_code not in self.black_list):
                test_success = self.test_connection(filename)
                if (test_success and (split_name[0] not in self.active_list)):  # If connection can be established and is not yet imported
                    self.import_ovpn(filename)
                elif (not test_success and (split_name[0] in self.active_list)):  # If connection failed and it is in our active list, remove it.
                    self.remove_connection(split_name[0])
                    self.purged.append(split_name[0])

            # Remove any purged from the active list, since we're done syncing
            for connection in purged:
                self.active_list.remove(connection)


class NotSudo(Exception):
    pass


importer = Importer()
importer.start()
