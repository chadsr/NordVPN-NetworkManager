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

"""
Features:
- blacklist certain countriescountry_blacklist = []
- auto import new connections (whilst removing old, non-existent ones)
- Change default connect on each run (maybe random, or select a set of countries)

sudo nmcli connection import type openvpn file <FILE>

TODO: Check if file has been modified and if so, replace old one with it
"""


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

    def start(self):
        args = self.parser.parse_args()

        if args.sync:
            self.sync_imports()
        elif args.purge:
            self.purge_active_connections()
        elif args.clean_sync:
            self.purge_active_connections()
            self.sync_imports()
        else:
            self.sync_imports()

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
                if (test_success and (split_name[0] not in self.active_list)): # If connection can be established and is not yet imported
                    self.import_ovpn(filename)
                elif (not test_success and (split_name[0] in self.active_list)): # If connection failed and it is in our active list, remove it.
                    self.remove_connection(split_name[0])
                    self.purged.append(split_name[0])

            # Remove any purged from the active list, since we're done syncing
            for connection in purged:
                self.active_list.remove(connection)


class NotSudo(Exception):
    pass


importer = Importer()
importer.start()
