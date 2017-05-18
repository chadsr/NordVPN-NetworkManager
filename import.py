#!/usr/bin/env python3
import configparser
import argparse

from urllib import error, parse, request
from os.path import basename
import os, datetime, time
import sys
import subprocess
from io import BytesIO
from zipfile import ZipFile
import requests
import keyring
from time import sleep

import logging

import pickle

# Temp
import json

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
        #__attr__?
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
        logging.basicConfig(filename='error.log', level=logging.ERROR)

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

    def start(self):
        self.download_configs("https://nordvpn.com/api/files/zip")
        self.sync_imports()
        self.save_active_list(self.active_list, LIST_PATH)
        subprocess.run("sudo service network-manager restart", shell=True, check=True)

    def add_credentials(self, filename):
        config = configparser.ConfigParser()
        path = "/etc/NetworkManager/system-connections/"+filename

        if os.path.isfile(path):
            config.read(path)
        elif os.path.isfile(path+'_'):
            path = path+'_'
            config.read(path)
        else:
            print ("No config file found!", path)
            return

        config['vpn']['password-flags'] = "0"
        config['vpn']['username'] = self.config.get_username()
        config['vpn-secrets'] = {}
        config['vpn-secrets']['password'] = self.config.get_password()

        with open(path, 'w') as config_file:
            config.write(config_file)

    def import_ovpn(self, filename):
        subprocess.run("nmcli connection import type openvpn file "+DATA_DIR+filename, shell=True, check=True)
        split_name = os.path.splitext(filename)
        self.add_credentials(split_name[0])
        self.active_list.append(split_name[0])

    def remove_connection(self, connection_name):
        subprocess.run("nmcli connection delete "+connection_name, shell=True, check=True)
        print (connection_name)
        self.active_list.remove(connection_name)

    def download_configs(self, url):
        try:
            uo = request.urlopen(url, timeout=TIMEOUT)
            zipfile = ZipFile(BytesIO(uo.read()))

            zipfile.extractall(DATA_DIR)
        except (error.URLError) as e:
            logging.error(e)

    def load_active_list(self, path):
        with open (LIST_PATH, 'rb') as fp:
            itemlist = pickle.load(fp)
        return itemlist

    def save_active_list(self, itemlist, path):
        with open(LIST_PATH, 'wb') as fp:
            pickle.dump(itemlist, fp)

    def get_country_code(self, connection_name):
        # hacky
        return connection_name[:2]

    def sync_imports(self):
        # first check if anything needs purging from the existing connections
        for connection in self.active_list:
            if self.get_country_code(connection) in self.black_list:
                self.remove_connection(connection)

        # Then begin checking for new
        for filename in os.listdir(DATA_DIR):
            split_name = os.path.splitext(filename)
            country_code = self.get_country_code(filename)

            if self.white_list:
                if (split_name[0] not in self.active_list) and (country_code in self.white_list):
                    self.import_ovpn(filename)
            else:
                if (split_name[0] not in self.active_list) and (country_code not in self.black_list):
                    self.import_ovpn(filename)

importer = Importer()
importer.start()
