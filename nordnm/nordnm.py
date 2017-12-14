from nordnm.credentials import CredentialsHandler
from nordnm.settings import SettingsHandler
from nordnm import nordapi
from nordnm import networkmanager
from nordnm import utils
from nordnm import benchmarking
from nordnm import paths
from nordnm.__init__ import __version__

import argparse
import os
import pickle
import sys
from fnmatch import fnmatch
import logging
import copy
from timeit import default_timer as timer


def generate_connection_name(server, protocol):
    short_name = server['domain'].split('.')[0]
    connection_name = short_name + ' ['

    for i, category in enumerate(server['categories']):
        category_name = nordapi.VPN_CATEGORIES[category['name']]
        if i > 0:  # prepend a separator if there is more than one category
            category_name = '|' + category_name

        connection_name = connection_name + category_name

    return connection_name + '] [' + protocol + ']'


class NordNM(object):
    def __init__(self):
        parser = argparse.ArgumentParser()

        features = parser.add_argument_group("Added Features")
        features.add_argument('-k', '--kill-switch', help='Sets a network kill-switch, to disable the active network interface when an active VPN connection disconnects.', action='store_true')
        features.add_argument('-a', '--auto-connect', nargs=3, metavar=('[COUNTRY_CODE]', '[VPN_CATEGORY]', '[PROTOCOL]'), help='Configure NetworkManager to auto-connect to the chosen server type. Takes country code, category and protocol.')

        removal = parser.add_argument_group("Remove")
        removal.add_argument('-r', '--remove', nargs='?', choices=['all', 'kill-switch', 'auto-connect'], const='all', help='(Default=all) Remove all active connections, auto-connect and kill-switch, or a specific choice.')

        update = parser.add_argument_group("Change Stored Data")
        update.add_argument('--credentials', help='Change your existing saved credentials.', action='store_true')
        update.add_argument('--settings', help='Change the existing saved settings.', action='store_true')

        info = parser.add_argument_group("Display Information")
        info.add_argument('--countries', help='Display a list of the available countries.', action='store_true')
        info.add_argument('--categories', help='Display a list of the available VPN categories..', action='store_true')

        subparser = parser.add_subparsers(title="Synchronise", dest='sync', metavar='')
        sync_parser = subparser.add_parser('sync', help="Synchronise the optimal servers (based on load and latency) to NetworkManager.")
        sync_parser.add_argument('-p', '--preserve-vpn',  help="When provided, synchronising will preserve any active VPN instead of disabling it for more accurate benchmarking.", action='store_true')
        sync_parser.add_argument('-u', '--update-configs', help='Download the latest OpenVPN configurations from NordVPN.', action='store_true', default=False)
        sync_parser.set_defaults(sync=True)

        self.logger = logging.getLogger(__name__)

        try:
            args = parser.parse_args()
            print(args)
        except Exception:
            parser.print_help()
            sys.exit(1)

        # Count the number of arguments provided
        arg_count = 0
        for arg in vars(args):
            if getattr(args, arg):
                arg_count += 1

        if arg_count == 0:
            parser.print_help()
            sys.exit(0)

        self.setup()

        # Check for commands that should be run on their own

        if args.remove:
            # Remove the auto-connect for all options other than "kill-switch"
            if args.remove != "kill-switch":
                networkmanager.remove_autoconnect()

            # Remove the kill-switch for all options other than "auto-connect"
            if args.remove != "auto-connect":
                networkmanager.remove_killswitch(paths.KILLSWITCH)

            if args.remove == "all":
                self.remove_active_connections()

            sys.exit(0)
        elif args.categories:
            self.print_categories()
            sys.exit(0)
        elif args.countries:
            self.print_countries()
            sys.exit(0)

        # Now check for commands that can be chained...

        if args.credentials:
            self.credentials.save_new_credentials()

        if args.settings:
            self.settings.save_new_settings()

        if args.sync:
            self.sync(args.update_configs, args.preserve_vpn)

        if args.auto_connect:
            country_code = args.auto_connect[0]
            category = args.auto_connect[1]
            protocol = args.auto_connect[2]
            self.enable_auto_connect(country_code, category, protocol)

        if args.kill_switch:
            networkmanager.set_killswitch(paths.KILLSWITCH)

        sys.exit(0)

    def print_splash(self):
        version_string = __version__

        latest_version = utils.get_pypi_package_version(__package__)
        if latest_version and version_string != latest_version:  # There's a new version on PyPi
            version_string = version_string + " (v" + latest_version + " available!)"
        elif latest_version and version_string == latest_version:
            version_string = version_string + " (Latest)"

        print("     _   _               _ _   _ ___  ___\n    | \ | |             | | \ | ||  \/  |\n    |  \| | ___  _ __ __| |  \| || .  . |\n    | . ` |/ _ \| '__/ _` | . ` || |\/| |\n    | |\  | (_) | | | (_| | |\  || |  | |\n    \_| \_/\___/|_|  \__,_\_| \_/\_|  |_/   v%s\n" % version_string)

    def print_categories(self):
        for long_name, short_name in nordapi.VPN_CATEGORIES.items():
            print("%-9s (%s)" % (short_name, long_name))

    def print_countries(self):
        servers = nordapi.get_server_list(sort_by_country=True)
        if servers:
            format_string = "| %-14s | %-4s |"
            countries = []

            print("\n Note: You must use the country code, NOT the country name in this tool.\n")
            print(format_string % ("NAME", "CODE"))
            print("|----------------+------|")

            for server in servers:
                country_code = server['flag']
                if country_code not in countries:
                    countries.append(country_code)
                    country_name = server['country']
                    print(format_string % (country_name, country_code))
        else:
            self.logger.error("Could not get available countries from the NordVPN API.")

    def setup(self):
        self.create_directories()

        self.settings = SettingsHandler(paths.SETTINGS)
        self.credentials = CredentialsHandler(paths.CREDENTIALS)

        self.black_list = self.settings.get_blacklist()
        self.white_list = self.settings.get_whitelist()

        self.active_servers = {}
        if os.path.isfile(paths.ACTIVE_SERVERS):
            self.active_servers = self.load_active_servers(paths.ACTIVE_SERVERS)

        self.print_splash()

    def sync(self, update_config=True, preserve_vpn=False):
        if update_config:
            self.get_configs()

        if self.sync_servers(preserve_vpn):
            networkmanager.reload_connections()

    def create_directories(self):
        if not os.path.exists(paths.DIR_ROOT):
            os.mkdir(paths.DIR_ROOT)
            utils.chown_path_to_user(paths.DIR_ROOT)

        if not os.path.exists(paths.DIR_OVPN):
            os.mkdir(paths.DIR_OVPN)
            utils.chown_path_to_user(paths.DIR_OVPN)

    def get_configs(self):
        self.logger.info("Downloading latest NordVPN OpenVPN configuration files to '%s'." % paths.DIR_OVPN)

        configs = nordapi.get_configs()
        if configs:
            if not utils.extract_zip(configs, paths.DIR_OVPN):
                self.logger.error("Failed to extract configuration files")
        else:
            self.logger.error("Failed to retrieve configuration files from NordVPN")

    def get_ovpn_path(self, domain, protocol):
        wildcard = domain + '.' + protocol + '*'
        ovpn_path = None

        try:
            for f in os.listdir(paths.DIR_OVPN):
                file_path = os.path.join(paths.DIR_OVPN, f)
                if os.path.isfile(file_path):
                    if fnmatch(f, wildcard):
                        ovpn_path = os.path.join(paths.DIR_OVPN, f)

        except Exception as ex:
            self.logger.error(ex)

        return ovpn_path

    def enable_auto_connect(self, country_code, category='normal', protocol='tcp'):
        enabled = False
        selected_parameters = (country_code.upper(), category, protocol)

        if selected_parameters in self.active_servers:
            connection_name = self.active_servers[selected_parameters]['name']

            if networkmanager.set_auto_connect(connection_name):
                networkmanager.disconnect_active_vpn(self.active_servers)
                if networkmanager.enable_connection(connection_name):
                    enabled = True
        else:
            self.logger.error("Auto-connect not activated: No active server found matching [%s, %s, %s].", country_code, category, protocol)

        return enabled

    def remove_active_connections(self):
        if self.active_servers:
            self.logger.info("Removing all active connections...")
            active_servers = copy.deepcopy(self.active_servers)
            for key in self.active_servers.keys():
                connection_name = self.active_servers[key]['name']
                if self.connection_exists(connection_name):
                    networkmanager.remove_connection(connection_name)

                del active_servers[key]
                self.save_active_servers(active_servers, paths.ACTIVE_SERVERS)  # Save after every successful removal, in case importer is killed abruptly

            self.active_servers = active_servers

            return True
        else:
            self.logger.info("No active connections to remove.")

    def load_active_servers(self, path):
        try:
            with open(paths.ACTIVE_SERVERS, 'rb') as fp:
                active_servers = pickle.load(fp)
            return active_servers
        except Exception as ex:
            self.logger.error(ex)
            return None

    def save_active_servers(self, active_servers, path):
        try:
            with open(paths.ACTIVE_SERVERS, 'wb') as fp:
                pickle.dump(active_servers, fp)
            utils.chown_path_to_user(paths.ACTIVE_SERVERS)
        except Exception as ex:
            self.logger.error(ex)

    def country_is_selected(self, country_code):
        # If (there is a whitelist and the country code is whitelisted) or (there is no whitelist, but there is a blacklist and it's not in the blacklist) or (there is no whitelist or blacklist)
        if (self.white_list and country_code in self.white_list) or (not self.white_list and self.black_list and country_code not in self.black_list) or (not self.white_list and not self.black_list):
            return True
        else:
            return False

    def has_valid_categories(self, server):
        valid_categories = self.settings.get_categories()

        # If the server has a category that is valid, return true
        for category in server['categories']:
            if category['name'] in valid_categories:
                return True

        return False

    def has_valid_protocol(self, server):
        valid_protocols = self.settings.get_protocols()
        has_openvpn_tcp = server['features']['openvpn_tcp']
        has_openvpn_udp = server['features']['openvpn_udp']

        if ('tcp' in valid_protocols and has_openvpn_tcp) or ('udp' in valid_protocols and has_openvpn_udp):
            return True
        else:
            return False

    def get_valid_servers(self, servers):
        valid_server_list = []

        for server in servers:
            country_code = server['flag']

            # If the server country has been selected, it has a selected protocol and selected categories
            if self.country_is_selected(country_code) and self.has_valid_protocol(server) and self.has_valid_categories(server):
                valid_server_list.append(server)

        return valid_server_list

    def connection_exists(self, connection_name):
        vpn_connections = networkmanager.get_vpn_connections()

        if vpn_connections and connection_name in vpn_connections:
            return True
        else:
            return False

    def configs_exist(self):
        configs = os.listdir(paths.DIR_OVPN)
        if configs:
            return True
        else:
            return False

    def sync_servers(self, preserve_vpn):
        updated = False

        username = self.credentials.get_username()
        password = self.credentials.get_password()
        dns_list = nordapi.get_nameservers()

        self.logger.info("Checking for new connections to import...")

        if self.configs_exist():

            server_list = nordapi.get_server_list(sort_by_load=True)
            if server_list:

                valid_server_list = self.get_valid_servers(server_list)
                if valid_server_list:

                    if not preserve_vpn:
                        # If there's a kill-switch in place, we need to temporarily remove it, otherwise it will kill out network when disabling an active VPN below
                        # Disconnect active Nord VPNs, so we get a more reliable benchmark
                        show_warning = False
                        if networkmanager.remove_killswitch(paths.KILLSWITCH):
                            show_warning = True
                            warning_string = "Kill-switch"
                        if networkmanager.disconnect_active_vpn(self.active_servers):
                            if show_warning:
                                warning_string = "Active VPN(s) and " + warning_string
                            else:
                                show_warning = True
                                warning_string = "Active VPN(s)"

                        if show_warning:
                            self.logger.warning("%s disabled for accurate benchmarking. Your connection is not secure until these are re-enabled.", warning_string)
                    else:
                        self.logger.warning("Active VPN preserved. This may give unreliable results!")

                    self.logger.info("Benchmarking servers...")

                    start = timer()
                    ping_attempts = self.settings.get_ping_attempts()  # We are going to be multiprocessing within a class instance, so this needs getting outside of the multiprocessing
                    valid_protocols = self.settings.get_protocols()
                    best_servers = benchmarking.get_best_servers(valid_server_list, ping_attempts, valid_protocols)

                    end = timer()
                    self.logger.info("Benchmarking complete. Took %0.2f seconds.", end - start)

                    # remove all old connections and any auto-connect, until a better sync routine is added
                    if self.remove_active_connections():
                        updated = True
                    if networkmanager.remove_autoconnect():
                        updated = True

                    self.logger.info("Adding new connections...")

                    new_connections = 0
                    for key in best_servers.keys():
                        imported = True
                        name = best_servers[key]['name']

                        if not self.connection_exists(name):
                            domain = best_servers[key]['domain']
                            protocol = key[2]

                            file_path = self.get_ovpn_path(domain, protocol)
                            if file_path:
                                if networkmanager.import_connection(file_path, name, username, password, dns_list):
                                    updated = True
                                    new_connections += 1
                                else:
                                    imported = False
                            else:
                                self.logger.warning("Could not find a configuration file for %s. Skipping.", name)

                        # If the connection already existed, or the import was successful, add the server combination to the active servers
                        if imported:
                            self.active_servers[key] = best_servers[key]
                            self.save_active_servers(self.active_servers, paths.ACTIVE_SERVERS)

                    if new_connections > 0:
                        self.logger.info("%i new connections added.", new_connections)
                    else:
                        self.logger.info("No new connections added.")

                    return updated
                else:
                    self.logger.error("No servers found matching your settings. Review your settings and try again.")
                    sys.exit(1)
            else:
                self.logger.error("Could not fetch the server list from NordVPN. Check your Internet connectivity.")
                sys.exit(1)
        else:
            self.logger.error("Can't find any OpenVPN configuration files. Please run --update before syncing.")
            sys.exit(1)
