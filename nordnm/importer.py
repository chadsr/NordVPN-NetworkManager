from config import ConfigHandler
from credentials import CredentialsHandler
import nordapi
import networkmanager
import utils
import benchmarking

import argparse
import os
import pickle
import sys
from collections import defaultdict
from fnmatch import fnmatch
import logging
from timeit import default_timer as timer

# TODO: Terminate script/wait cleanly if network connection goes down

# TODO: Put these paths somewhere more appropriate
HOME_DIR = os.path.expanduser('~' + utils.get_current_user())
USER_DIR = os.path.join(HOME_DIR, '.nordnm/')
OVPN_DIR = os.path.join(USER_DIR, 'configs/')
CONFIG_PATH = os.path.join(USER_DIR, 'settings.conf')

ROOT_DIR = '/usr/share/nordnm/'
LIST_PATH = os.path.join(ROOT_DIR, 'active.list')
CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'credentials')


class Importer(object):
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-u', '--update', help='Get the latest OpenVPN configuration files from NordVPN', action='store_true')
        parser.add_argument('-s', '--sync', help="Synchronise best servers (based on load and latency) to NetworkManager", action="store_true")
        parser.add_argument('-p', '--purge', help='Remove all active connections and auto-connect (if configured)', action='store_true')
        parser.add_argument('-a', '--auto-connect', nargs=3, metavar=('[COUNTRY_CODE]', '[VPN_TYPE]', '[PROTOCOL]'), help='Configure NetworkManager to always auto-connect to the lowest latency server. Takes country code, category and protocol')

        try:
            args = parser.parse_args()
        except:
            sys.exit(1)

        if args.update or args.sync or args.purge or args.auto_connect:
            self.run(args.update, args.sync, args.purge, args.auto_connect)
        else:
            parser.print_help()

    def setup(self):
        self.logger = logging.getLogger(__name__)

        self.create_directories()

        self.config = ConfigHandler(CONFIG_PATH)
        self.credentials = CredentialsHandler(CREDENTIALS_PATH)

        self.black_list = self.config.get_blacklist()
        self.white_list = self.config.get_whitelist()

        self.active_list = []
        if os.path.isfile(LIST_PATH):
            self.active_list = self.load_active_list(LIST_PATH)

        self.best_servers = defaultdict(dict)

    def run(self, update, sync, purge, auto_connect):
        updated = False

        self.setup()

        if update:
            self.get_configs()
        if sync:
            updated = self.sync_servers()
        elif purge:
            updated = self.purge_active_connections()

        if auto_connect:
            updated = self.select_auto_connect(auto_connect[0], auto_connect[1], auto_connect[2])

        if updated:
            networkmanager.restart()

    def create_directories(self):
        if not os.path.exists(USER_DIR):
            os.mkdir(USER_DIR)
            utils.chown_path_to_user(USER_DIR)

        if not os.path.exists(OVPN_DIR):
            os.mkdir(OVPN_DIR)
            utils.chown_path_to_user(OVPN_DIR)

        if not os.path.exists(ROOT_DIR):
            os.mkdir(ROOT_DIR)

    def get_configs(self):
        self.logger.info("Attempting to download and extract the latest NordVPN configurations.")

        configs = nordapi.get_configs()
        if configs:
            utils.extract_zip(configs, OVPN_DIR)
        else:
            self.logger.error("Could not retrieve configs from NordVPN")

    def get_ovpn_path(self, domain, protocol):
        wildcard = domain+'.'+protocol+'*'
        ovpn_path = None

        try:
            for f in os.listdir(OVPN_DIR):
                file_path = os.path.join(OVPN_DIR, f)
                if os.path.isfile(file_path):
                    if fnmatch(f, wildcard):
                        ovpn_path = os.path.join(OVPN_DIR, f)

        except Exception as ex:
            self.logger.error(ex)

        return ovpn_path

    def select_auto_connect(self, country_code, category='normal', protocol='tcp'):
        selected_parameters = (country_code.upper(), category, protocol)

        if selected_parameters in self.best_servers:
            connection_name = self.best_servers[selected_parameters]['name']
            logging.info("Setting '%s' as auto-connect server.", connection_name)
            networkmanager.set_auto_connect(connection_name)
            return True
        else:
            self.logger.warning("No active server found matching %s %s %s. Check your input and try again.")
            return False

    def purge_active_connections(self, remove_autoconnect=True):
        if remove_autoconnect:
            removed = networkmanager.remove_autoconnect()
            if removed:
                self.logger.info("Auto-Connect file removed.")

        if self.active_list:
            self.logger.info("Removing all active connections...")
            for connection in self.active_list:
                networkmanager.remove_connection(connection)

            self.active_list = []
            self.save_active_list(self.active_list, LIST_PATH)

            self.logger.info("All active connections removed!")

            return True
        else:
            self.logger.info("No active connections to remove.")

    def load_active_list(self, path):
        try:
            with open(LIST_PATH, 'rb') as fp:
                itemlist = pickle.load(fp)
            return itemlist
        except Exception as ex:
            self.logger.error(ex)
            return None

    def save_active_list(self, itemlist, path):
        try:
            with open(LIST_PATH, 'wb') as fp:
                pickle.dump(itemlist, fp)
        except Exception as ex:
            self.logger.error(ex)

    def country_is_selected(self, country_code):
        # If (there is a whitelist and the country code is whitelisted) or (there is no whitelist, but there is a blacklist and it's not in the blacklist) or (there is no whitelist or blacklist)
        if (self.white_list and country_code in self.white_list) or (not self.white_list and self.black_list and country_code not in self.black_list) or (not self.white_list and not self.black_list):
            return True
        else:
            return False

    def get_valid_servers(self):
        full_server_list = nordapi.get_server_list(sort_by_load=True)

        if full_server_list:
            valid_server_list = []

            for server in full_server_list:
                country_code = server['flag']
                has_openvpn_tcp = server['features']['openvpn_tcp']
                has_openvpn_udp = server['features']['openvpn_udp']

                # If the server country has been selected and the server has OpenVPN enabled
                if self.country_is_selected(country_code) and (has_openvpn_tcp or has_openvpn_udp):
                    valid_server_list.append(server)

            return valid_server_list
        else:
            self.logger.error("Could not fetch the server list from NordVPN.")
            return None

    def configs_exist(self):
        configs = os.listdir(OVPN_DIR)
        if configs:
            return True
        else:
            return False

    def sync_servers(self):
        updated = False

        username = self.credentials.get_username()
        password = self.credentials.get_password()
        dns_list = nordapi.get_nameservers()

        self.logger.info("Checking for new connections to import...")

        if self.configs_exist():
            valid_server_list = self.get_valid_servers()
            if valid_server_list:
                networkmanager.disconnect_active_vpn(self.active_list)  # Disconnect active Nord VPNs, so we get a more reliable benchmark

                ping_attempts = self.config.get_ping_attempts()  # We are going to be multiprocessing within a class instance, so this needs getting outside of the multiprocessing
                self.logger.info("Finding best servers to synchronise...")

                start = timer()
                self.best_servers = benchmarking.get_best_servers(valid_server_list, ping_attempts)
                end = timer()
                self.logger.info("Done benchmarking. Took %0.2f seconds.", end-start)

                updated = self.purge_active_connections()  # Purge all old connections until a better sync routine is added

                new_connections = 0
                for key in self.best_servers.keys():
                    if self.best_servers[key]:
                        domain = self.best_servers[key]['domain']
                        protocol = key[2]
                        name = self.best_servers[key]['name']

                        if name not in self.active_list:
                            file_path = self.get_ovpn_path(domain, protocol)
                            if file_path:
                                if networkmanager.import_connection(file_path, name, username, password, dns_list):
                                    updated = True
                                    new_connections += 1
                                    self.active_list.append(name)
                                    self.save_active_list(self.active_list, LIST_PATH)
                            else:
                                self.logger.warning("Could not find a configuration file for %s. Skipping.", name)

                if new_connections > 0:
                    self.logger.info("%i new connections added.", new_connections)
                else:
                    self.logger.info("No new connections added.")

                return updated
            else:
                self.logger.error("No servers found to sync. Exiting.")
                sys.exit(1)
        else:
            self.logger.error("Can't find any OpenVPN configuration files. Please run --update before syncing.")
            sys.exit(1)
