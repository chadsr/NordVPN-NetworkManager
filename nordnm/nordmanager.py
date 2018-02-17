from nordnm.credentials import CredentialsHandler
from nordnm.settings import SettingsHandler
from nordnm import nordapi
from nordnm import networkmanager
from nordnm import utils
from nordnm import benchmarking
from nordnm import paths

import os
import shutil
import pickle
import sys
import glob
import copy
from timeit import default_timer as timer
from nordnm import log


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
        self.ensure_config_dirs()
        self._active_servers = None
        self.settings = SettingsHandler(paths.SETTINGS)
        self.credentials = CredentialsHandler(paths.CREDENTIALS)
        self.country_blacklist = self.settings.get_blacklist()
        self.country_whitelist = self.settings.get_whitelist()
        self._config_info = None

    @property
    def config_info(self):
        if not self._config_info:
            with open(paths.CONFIG_INFO, 'r') as f:
                self._config_info = f.read().replace('\n', '')
        return self._config_info

    @config_info.setter
    def config_info(self, value):
        with open(paths.CONFIG_INFO, 'w') as f:
            f.write(value)
        self._config_info = value

    @property
    def active_servers(self):
        if self._active_servers:
            return self._active_servers
        try:
            with open(paths.ACTIVE_SERVERS, 'rb') as fp:
                self._active_servers = pickle.load(fp)
        except FileNotFoundError:
            log.error('No active servers found, use sync command to setup servers')
        return self._active_servers

    @active_servers.setter
    def active_servers(self, value):
        with open(paths.ACTIVE_SERVERS, 'wb') as fp:
            pickle.dump(value, fp)
        utils.chown_path_to_user(paths.ACTIVE_SERVERS)

    def delete_configs(self):
        for f in os.listdir(paths.OVPN_CONFIGS):
            file_path = os.path.join(paths.OVPN_CONFIGS, f)
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

    def download_configs(self):
        log.info(f"Downloading latest NordVPN OpenVPN configuration files to '{paths.OVPN_CONFIGS}'.")
        try:
            zip_file, etag = nordapi.get_ovpn_configs()
        except ValueError:
            log.info("Configuration files already up-to-date.")
            return
        self.delete_configs()
        utils.extract_zip(zip_file, paths.OVPN_CONFIGS)
        self.config_info = etag

    def sync(self, preserve_vpn=False):
        # remove legacy files
        if self.sync_servers(preserve_vpn):
            networkmanager.reload_connections()

    def ensure_config_dirs(self):
        try:
            os.mkdir(paths.ROOT)
            utils.chown_path_to_user(paths.ROOT)
            os.mkdir(paths.OVPN_CONFIGS)
            utils.chown_path_to_user(paths.OVPN_CONFIGS)
        except FileExistsError:
            pass

    def get_ovpn_path(self, domain, protocol):
        files = glob.glob(paths.OVPN_CONFIGS + '/**/' + domain + '.' + protocol + '*.ovpn')
        return (files or [None])[0]

    def enable_auto_connect(self, country_code: str, category: str = 'normal', protocol: str = 'tcp'):
        enabled = False
        selected_parameters = (country_code.upper(), category, protocol)

        if selected_parameters in self.active_servers:
            connection_name = self.active_servers[selected_parameters]['name']
            connection_load = self.active_servers[selected_parameters]['load']
            connection_latency = self.active_servers[selected_parameters]['latency']

            if networkmanager.set_auto_connect(connection_name):
                log.info(f"Auto-connect enabled for '{connection_name}' "
                         f"(Load: {connection_load}%, Latency: {connection_latency:.2f}).")
                networkmanager.disconnect_active_vpn(self.active_servers)
                if networkmanager.enable_connection(connection_name):
                    enabled = True
        else:
            log.error(f"Auto-connect not activated: No active server found "
                      f"matching [{country_code}, {category}, {protocol}].")

        return enabled

    def is_valid_server(self, server):
        def server_has_valid_country():
            country_code = server['flag']
            if not self.country_blacklist and not self.country_whitelist:
                return True
            if self.country_whitelist and country_code and self.country_whitelist:
                return True
            if not self.country_whitelist and self.country_blacklist and country_code not in self.country_blacklist:
                return True
            return False

        def server_has_valid_categories():
            valid_categories = self.settings.get_categories()

            # If the server has a category that is valid, return true
            for category in server['categories']:
                if category['name'] in valid_categories:
                    return True

            return False

        def server_has_valid_protocol():
            valid_protocols = self.settings.get_protocols()
            has_openvpn_tcp = server['features']['openvpn_tcp']
            has_openvpn_udp = server['features']['openvpn_udp']

            if ('tcp' in valid_protocols and has_openvpn_tcp) or ('udp' in valid_protocols and has_openvpn_udp):
                return True
            else:
                return False

        return server_has_valid_country() and server_has_valid_protocol() and server_has_valid_categories()

    def connection_exists(self, connection_name):
        return connection_name in networkmanager.get_vpn_connections()

    def configs_exist(self):
        return bool(os.listdir(paths.OVPN_CONFIGS))

    def get_best_servers(self, servers):
        log.info("Benchmarking servers...")
        start = timer()
        best_servers = benchmarking.get_best_servers(servers,
                                                     self.settings.get_ping_attempts(),
                                                     self.settings.get_protocols())
        end = timer()
        log.info(f"Benchmarking complete. Took {end - start:.2f} seconds.")
        return best_servers

    def sync_servers(self, preserve_vpn):
        # remove legacy
        for file_path in paths.LEGACY_FILES:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
        log.info("Checking for new connections to import...")
        server_list = nordapi.get_server_list(sort_by_load=True)
        if not server_list:
            log.error("Could not fetch the server list from NordVPN. Check your Internet connectivity.")
            sys.exit(1)
        server_list = [s for s in server_list if self.is_valid_server(s)]
        if not server_list:
            log.error("No servers found matching your settings. Review your settings and try again.")
            sys.exit(1)
        if preserve_vpn:
            log.warning("Active VPN preserved. This may give unreliable results!")
        else:
            # If there's a kill-switch in place, we need to temporarily remove it,
            # otherwise it will kill out network when disabling an active VPN below
            # Disconnect active Nord VPNs, so we get a more reliable benchmark
            warnings = {
                'Kill-switch': networkmanager.remove_killswitch(),
                'Active VPN(s)': networkmanager.disconnect_active_vpn(self.active_servers),
            }
            if any(warnings.values()):
                log.warning(f"{', '.join(warnings.keys())} disabled for accurate benchmarking. "
                            f"Your connection is not secure until these are re-enabled.")

        # remove all old connections and any auto-connect, until a better sync routine is added
        self.active_servers = {}
        networkmanager.remove_autoconnect()

        log.info("Adding new connections...")
        new_servers = {}
        for key, server in self.get_best_servers(server_list).items():
            if self.connection_exists(server['name']):
                new_servers[key] = server
                continue
            file_path = self.get_ovpn_path(server['domain'], key[2])
            if not file_path:
                log.warning(f"Could not find a configuration file for {server['name']}. Skipping.")
                continue
            networkmanager.import_connection(
                    file_path, server['name'],
                    self.credentials.get_username(),
                    self.credentials.get_password(),
                    nordapi.get_nameservers()
            )
            new_servers[key] = server
        if len(new_servers) > 0:
            self.active_servers = {**self.active_servers, **new_servers}
            log.info(f"{len(new_servers)} new connections added.")
        else:
            log.info("No new connections added.")


