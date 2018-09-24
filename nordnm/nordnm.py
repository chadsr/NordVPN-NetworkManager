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
import shutil
import pickle
import sys
import glob
import logging
import copy
from timeit import default_timer as timer
from distutils.version import StrictVersion


IMPORTED_SERVER_KEY = ('(imported)', '', '')


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
        subparsers = parser.add_subparsers(title="commands", help="Each command has its own help page, which can be accessed via nordnm <COMMAND> --help", metavar='')

        # Kill-switch and auto-connect are repeated, to allow their use with or without the sync command.
        # TODO: Find out if there's a way to re-use the attributes so they don't need to be manually repeated
        parser.add_argument("-v", "--version", help="Display the package version.", action="store_true")
        parser.add_argument("-k", "--kill-switch", help="Sets a network kill-switch, to disable the active network interface when an active VPN connection disconnects.", action="store_true")
        parser.add_argument("-a", "--auto-connect", nargs=3, metavar=("[COUNTRY_CODE]", "[VPN_CATEGORY]", "[PROTOCOL]"), help="Configure NetworkManager to auto-connect to the chosen server type. Takes country code, category and protocol.")

        remove_parser = subparsers.add_parser("remove", aliases=['r'], help="Remove active connections, auto-connect, kill-switch, data, mac settings or all.")
        remove_parser.add_argument("--all", dest="remove_all", help="Remove all connections, enabled features and local data.", action="store_true")
        remove_parser.add_argument("-c", "--connections", dest="remove_c", help="Remove all active connections and auto-connect.", action="store_true")
        remove_parser.add_argument("-a", "--auto-connect", dest="remove_ac", help="Remove the active auto-connect feature.", action="store_true")
        remove_parser.add_argument("-k", "--kill-switch", dest="remove_ks", help="Remove the active kill-switch feature.", action="store_true")
        remove_parser.add_argument("-d", "--data", dest="remove_d", help="Remove existing local data (VPN Configs, Credentials & Settings).", action="store_true")
        remove_parser.add_argument("-m", "--mac-settings", dest="remove_m", help="Remove existing MAC Address settings configured by nordnm.", action="store_true")
        remove_parser.set_defaults(remove=True)

        update_parser = subparsers.add_parser('update', aliases=['u'], help='Update a specified setting.')
        update_parser.add_argument('-c', '--credentials', help='Update your existing saved credentials.', action='store_true')
        update_parser.add_argument('-s', '--settings', help='Update your existing saved settings.', action='store_true')
        update_parser.set_defaults(update=True)

        list_parser = subparsers.add_parser('list', aliases=['l'], help="List the specified information.")
        list_parser.add_argument('--active-servers', help='Display a list of the active servers currently synchronised.', action='store_true', default=False)
        list_parser.add_argument('--countries', help='Display a list of the available NordVPN countries.', action='store_true', default=False)
        list_parser.add_argument('--categories', help='Display a list of the available NordVPN categories..', action='store_true', default=False)
        list_parser.set_defaults(list=True)

        sync_parser = subparsers.add_parser('sync', aliases=['s'], help="Synchronise the optimal servers (based on load and latency) to NetworkManager.")
        sync_parser.add_argument('-s', '--slow-mode', help="Run benchmarking in 'slow mode'. May increase benchmarking success by pinging servers at a slower rate.", action='store_true')
        sync_parser.add_argument('-p', '--preserve-vpn', help="When provided, synchronising will preserve any active VPN instead of disabling it for more accurate benchmarking.", action='store_true')
        sync_parser.add_argument('-u', '--update-configs', help='Download the latest OpenVPN configurations from NordVPN.', action='store_true', default=False)
        sync_parser.add_argument("-k", "--kill-switch", help="Sets a network kill-switch, to disable the active network interface when an active VPN connection disconnects.", action="store_true")
        sync_parser.add_argument('-a', '--auto-connect', nargs=3, metavar=('[COUNTRY_CODE]', '[VPN_CATEGORY]', '[PROTOCOL]'), help='Configure NetworkManager to auto-connect to the chosen server type. Takes country code, category and protocol.')
        sync_parser.set_defaults(sync=True)

        import_parser = subparsers.add_parser('import', aliases=['i'], help="Import an OpenVPN config file to NetworkManager.")
        import_parser.add_argument("config_file", metavar='CONFIG_FILE', help="The OpenVPN config file to be imported.")
        import_parser.add_argument("-k", "--kill-switch", help="Sets a network kill-switch, to disable the active network interface when an active VPN connection disconnects.", action="store_true")
        import_parser.add_argument('-a', '--auto-connect', help='Configure NetworkManager to auto-connect to the the imported config.', action="store_true", dest="auto_connect_imported", default=False)
        import_parser.add_argument('-u', '--username', required=True, help="Specify the username used for the OpenVPN config.", metavar="USERNAME")
        import_parser.add_argument('-p', '--password', required=True, help="Specify the password used for the OpenVPN config.", metavar="PASSWORD")
        import_parser.set_defaults(import_config=True)

        # For reference: https://blogs.gnome.org/thaller/category/networkmanager/
        mac_parser = subparsers.add_parser('mac', aliases=['m'], help="Global NetworkManager MAC address preferences. This command will affect ALL NetworkManager connections permanently.")
        mac_parser.add_argument('-r', '--random', help="A randomised MAC addresss will be generated on each connect.", action='store_true')
        mac_parser.add_argument('-s', '--stable', help="Use a stable, hashed MAC address on connect.", action='store_true')
        mac_parser.add_argument('-e', '--explicit', help="Specify a MAC address to use on connect.", nargs=1, metavar='"MAC_ADDRESS"')
        mac_parser.add_argument('--preserve', help="Don't change the current MAC address upon connection.", action='store_true')
        mac_parser.add_argument('--permanent', help="Use the permanent MAC address of the device on connect.", action='store_true')
        mac_parser.set_defaults(mac=True)

        self.logger = logging.getLogger(__name__)
        self.active_servers = {}

        try:
            args = parser.parse_args()
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
            sys.exit(1)

        if "version" in args and args.version:
            print(__version__)
            sys.exit(1)

        self.print_splash()

        # Check for commands that should be run on their own
        if "remove" in args and args.remove:
            removed = False

            if not args.remove_c and not args.remove_d and not args.remove_ac and not args.remove_ks and not args.remove_m and not args.remove_all:
                remove_parser.print_help()
                sys.exit(1)

            if args.remove_all:
                # Removing all, so set all args to True
                args.remove_ks = True
                args.remove_ac = True
                args.remove_c = True
                args.remove_d = True
                args.remove_m = True
            elif args.remove_c:
                # We need to remove the auto-connect if we are removing all connections
                args.remove_ac = True

            if args.remove_ks:
                if networkmanager.remove_killswitch():
                    removed = True

            if args.remove_ac:
                if networkmanager.remove_autoconnect():
                    removed = True

            if args.remove_c:
                # Get the active servers, since self.setup() hasn't run
                if os.path.isfile(paths.ACTIVE_SERVERS):
                    self.active_servers = self.load_active_servers(paths.ACTIVE_SERVERS)

                if self.remove_active_connections():
                    removed = True

            if args.remove_d:
                if self.remove_data():
                    removed = True

            if args.remove_m:
                if networkmanager.remove_global_mac_address():
                    removed = True

            if removed:
                networkmanager.reload_connections()
            else:
                self.logger.info("Nothing to remove.")

            sys.exit(0)
        elif "list" in args and args.list:
            if not args.countries and not args.categories and not args.active_servers:
                list_parser.print_help()
                sys.exit(1)

            if args.categories:
                self.print_categories()
            if args.countries:
                self.print_countries()
            if args.active_servers:
                self.print_active_servers()

            sys.exit(0)
        elif "mac" in args and args.mac:
            value = None
            if args.random:
                value = "random"
            elif args.stable:
                value = "stable"
            elif args.explicit:
                value = args.explicit[0]
            elif args.preserve:
                value = "preserve"
            elif args.permanent:
                value = "permanent"

            if value:
                if networkmanager.set_global_mac_address(value):
                    networkmanager.restart()
            else:
                mac_parser.print_help()

        # Now that arguments that don't need to be disturbed by setup() are over, do setup()
        self.setup()

        if "update" in args and args.update:
            if not args.credentials and not args.settings:
                update_parser.print_help()
                sys.exit(1)

            if args.credentials:
                self.credentials.save_new_credentials()
            if args.settings:
                self.settings.save_new_settings()

            sys.exit(0)

        # Now check for commands that can be chained...
        if "sync" in args and args.sync:
            self.sync(args.update_configs, args.preserve_vpn, args.slow_mode)

        if "import_config" in args and args.import_config:
            if not self.import_config(args.config_file, args.username, args.password):
                sys.exit(1)

            if args.auto_connect_imported:
                self.enable_auto_connect(*IMPORTED_SERVER_KEY)

        if args.kill_switch:
            networkmanager.set_killswitch()

        if args.auto_connect:
            country_code = args.auto_connect[0]
            category = args.auto_connect[1]
            protocol = args.auto_connect[2]

            self.enable_auto_connect(country_code, category, protocol)

        sys.exit(0)

    def print_splash(self):
        version_string = __version__

        latest_version = utils.get_pypi_package_version(__package__)
        if latest_version:
            if StrictVersion(version_string) < StrictVersion(latest_version):  # There's a new version on PyPi
                version_string = version_string + " (v" + latest_version + " available!)"
            else:
                version_string = version_string + " (Latest)"

        print("     _   _               _ _   _ ___  ___\n"
              "    | \ | |             | | \ | ||  \/  |\n"
              "    |  \| | ___  _ __ __| |  \| || .  . |\n"
              "    | . ` |/ _ \| '__/ _` | . ` || |\/| |\n"
              "    | |\  | (_) | | | (_| | |\  || |  | |\n"
              "    \_| \_/\___/|_|  \__,_\_| \_/\_|  |_/   v%s\n" % version_string)

    def print_categories(self):
        format_string = "| %-10s | %-20s |"
        print("\n Note: You must use the short name in this tool.\n")
        print(format_string % ("SHORT NAME", "LONG NAME"))
        print("|------------+----------------------|")

        for long_name, short_name in nordapi.VPN_CATEGORIES.items():
            print(format_string % (short_name, long_name))

        print()  # For spacing

    def print_countries(self):
        servers = nordapi.get_server_list(sort_by_country=True)
        if servers:
            format_string = "| %-22s | %-4s |"
            countries = []

            print("\n Note: You must use the country code, NOT the country name in this tool.\n")
            print(format_string % ("NAME", "CODE"))
            print("|------------------------+------|")

            for server in servers:
                country_code = server['flag']
                if country_code not in countries:
                    countries.append(country_code)
                    country_name = server['country']
                    print(format_string % (country_name, country_code))

            print()  # For spacing
        else:
            self.logger.error("Could not get available countries from the NordVPN API.")

    def print_active_servers(self):
        if os.path.isfile(paths.ACTIVE_SERVERS):
            self.active_servers = self.load_active_servers(paths.ACTIVE_SERVERS)

        if self.active_servers:
            print("Note: All metrics below are from the last synchronise.\n")
            format_string = "| %-16s | %-20s | %-8s | %-11s | %-8s |"
            print(format_string % ("PARAMETER", "SERVER", "LOAD (%)", "LATENCY (s)", "SCORE"))
            print("|------------------+----------------------+----------+-------------+----------|")

            for params in self.active_servers:
                parameters = ' '.join(params).lower()
                domain = self.active_servers[params]['domain']
                score = self.active_servers[params]['score']
                load = self.active_servers[params]['load']
                latency = round(self.active_servers[params]['latency'], 2)

                print(format_string % (parameters, domain, load, latency, score))

            print()  # For spacing
        else:
            self.logger.warning("No active servers to display.")

    def setup(self):
        self.create_directories()

        self.settings = SettingsHandler(paths.SETTINGS)
        self.credentials = CredentialsHandler(paths.CREDENTIALS)

        self.black_list = self.settings.get_blacklist()
        self.white_list = self.settings.get_whitelist()

        if os.path.isfile(paths.ACTIVE_SERVERS):
            self.active_servers = self.load_active_servers(paths.ACTIVE_SERVERS)

    def remove_legacy_files(self):
        removed = False
        for file_path in paths.LEGACY_FILES:
            try:
                os.remove(file_path)
                removed = True
            except FileNotFoundError:
                pass
            except Exception as e:
                self.logger.error("Error attempting to remove '%s': %s" % (file_path, e))

        return removed

    def set_config_info(self, etag):
        if os.path.exists(paths.OVPN_CONFIGS):
            with open(paths.CONFIG_INFO, 'w') as f:
                f.write(etag)

            return True
        else:
            return False

    def get_config_info(self):
        if os.path.exists(paths.CONFIG_INFO):
                with open(paths.CONFIG_INFO, 'r') as f:
                    info = f.read().replace('\n', '')

                return info
        else:
            return None

    def delete_configs(self):
        for f in os.listdir(paths.OVPN_CONFIGS):
            file_path = os.path.join(paths.OVPN_CONFIGS, f)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                self.logger.error("Could not delete config file: %s" % e)

    def get_configs(self):
        self.logger.info("Downloading latest NordVPN OpenVPN configuration files to '%s'." % paths.OVPN_CONFIGS)

        etag = self.get_config_info()
        config_data = nordapi.get_configs(etag)
        if config_data is False:
            self.logger.error("Failed to retrieve configuration files from NordVPN")
            return False
        elif config_data:
            zip_file, etag = config_data
            if zip_file and etag:
                self.delete_configs()

                if not utils.extract_zip(zip_file, paths.OVPN_CONFIGS):
                    self.logger.error("Failed to extract configuration files")
                    return False

                if not self.set_config_info(etag):
                    return False
            else:
                self.logger.info("Configuration files already up-to-date.")

            return True

    def sync(self, update_config=True, preserve_vpn=False, slow_mode=False):
        if self.remove_legacy_files():
            self.logger.info("Removed legacy files")

        if update_config:
            self.get_configs()

        if self.sync_servers(preserve_vpn, slow_mode):
            networkmanager.reload_connections()

    def import_config(self, file_path: str, username: str, password: str) -> bool:
        updated = False
        imported = False
        if self.remove_legacy_files():
            self.logger.info("Removed legacy files")

        if not os.path.isfile(file_path):
            self.logger.error("Configuration file '%s' does not exist.", file_path)
            return None

        # remove all old connections and any auto-connect, until a better import routine is added
        if self.remove_active_connections():
            updated = True
        if networkmanager.remove_autoconnect():
            updated = True

        dns_list = self.settings.get_custom_dns_servers()
        connection_name = os.path.splitext(os.path.basename(file_path))[0]
        if networkmanager.import_connection(file_path, connection_name, username, password,
                                            dns_list, create_temp_file=False):
            updated = True
            imported = True
            self.active_servers[IMPORTED_SERVER_KEY] = {
                'name': connection_name,
                'domain': '<' + connection_name + '>',
                'score': -1,
                'load': -1,
                'latency': -1,
            }
            self.save_active_servers(self.active_servers, paths.ACTIVE_SERVERS)

        if updated:
            networkmanager.reload_connections()

        return imported

    def remove_data(self):
        if os.path.exists(paths.ROOT):
            try:
                shutil.rmtree(paths.ROOT)
            except Exception as e:
                self.logger.error("Could not remove the data directory '%s': %s" % (paths.ROOT, e))
                return False
        else:
            self.logger.info("Data directory does not exist. Nothing to remove.")

        self.logger.info("Data directory '%s' removed successfully!" % paths.ROOT)
        return True

    def create_directories(self):
        if not os.path.exists(paths.ROOT):
            os.mkdir(paths.ROOT)
            utils.chown_path_to_user(paths.ROOT)

        if not os.path.exists(paths.OVPN_CONFIGS):
            os.mkdir(paths.OVPN_CONFIGS)
            utils.chown_path_to_user(paths.OVPN_CONFIGS)

    def get_ovpn_path(self, domain, protocol):
        ovpn_path = None

        try:
            files = glob.glob(paths.OVPN_CONFIGS + '/**/' + domain + '.' + protocol + '*.ovpn')
            ovpn_path = files[0]
        except Exception as ex:
            self.logger.error(ex)

        return ovpn_path

    def enable_auto_connect(self, country_code: str, category: str='normal', protocol: str='tcp'):
        enabled = False
        selected_parameters = (country_code.lower(), category.lower(), protocol.lower())

        if selected_parameters in self.active_servers:
            connection_name = self.active_servers[selected_parameters]['name']
            connection_load = self.active_servers[selected_parameters]['load']
            connection_latency = self.active_servers[selected_parameters]['latency']

            if networkmanager.set_auto_connect(connection_name):
                self.logger.info("Auto-connect enabled for '%s' (Load: %i%%, Latency: %0.2fs).", connection_name, connection_load, connection_latency)

                # Temporarily remove the kill-switch if there was one
                kill_switch = networkmanager.remove_killswitch(log=False)

                networkmanager.disconnect_active_vpn(self.active_servers)

                if kill_switch:
                    networkmanager.set_killswitch(log=False)

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
            country_code = server['flag'].lower()

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
        configs = os.listdir(paths.OVPN_CONFIGS)
        if configs:
            return True
        else:
            return False

    def sync_servers(self, preserve_vpn, slow_mode):
        updated = False

        username = self.credentials.get_username()
        password = self.credentials.get_password()

        # Check if there are custom DNS servers specified in the settings before loading the defaults
        dns_list = self.settings.get_custom_dns_servers()

        if not self.configs_exist():
            self.logger.warning("No OpenVPN configuration files found.")
            if not self.get_configs():
                sys.exit(1)

        self.logger.info("Checking for new connections to import...")

        server_list = nordapi.get_server_list(sort_by_load=True)
        if server_list:

            valid_server_list = self.get_valid_servers(server_list)
            if valid_server_list:

                if not preserve_vpn:
                    # If there's a kill-switch in place, we need to temporarily remove it, otherwise it will kill out network when disabling an active VPN below
                    # Disconnect active Nord VPNs, so we get a more reliable benchmark
                    show_warning = False
                    if networkmanager.remove_killswitch():
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

                if slow_mode:
                    self.logger.info("Benchmarking slow mode enabled.")

                num_servers = len(valid_server_list)
                self.logger.info("Benchmarking %i servers...", num_servers)

                start = timer()
                ping_attempts = self.settings.get_ping_attempts()  # We are going to be multiprocessing within a class instance, so this needs getting outside of the multiprocessing
                valid_protocols = self.settings.get_protocols()
                valid_categories = self.settings.get_categories()
                best_servers, num_success = benchmarking.get_best_servers(valid_server_list, ping_attempts, valid_protocols, valid_categories, slow_mode)

                end = timer()

                if num_success == 0:
                    self.logger.error("Benchmarking failed to test any servers. Your network may be blocking large-scale ICMP requests. Exiting.")
                    sys.exit(1)
                else:
                    percent_success = round(num_success / num_servers * 100, 2)
                    self.logger.info("Benchmarked %i servers successfully (%0.2f%%). Took %0.2f seconds.", num_success, percent_success, end - start)

                    if percent_success < 90.0:
                        self.logger.warning("A large quantity of tests failed. Your network may be unreliable, or blocking large-scale ICMP requests. Syncing in slow mode (-s) may fix this.")

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
