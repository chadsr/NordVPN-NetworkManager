from nordnm import utils
from nordnm import nordapi

import configparser
import logging
import os


class SettingsHandler(object):
    DEFAULT_PING_ATTEMPTS = 5

    def __init__(self, path):
        self.logger = logging.getLogger(__name__)

        self.path = path

        if not self.load():
            self.logger.warning("No existing settingss found!")
            # Prompt for new settings
            self.save_new_settings()

    def save_new_settings(self):
        self.logger.info("Prompting for new settings.\n")

        self.settings = configparser.ConfigParser(allow_no_value=True, interpolation=None)

        # Prompt for which countries to synchronise
        # First offer the whitelist, if the user chooses to skip the whitelist, offer the blacklist
        blacklist = ''
        whitelist = input("If you wish to synchronise only specific countries, enter their country codes separated by spaces. (Press enter to skip): ")
        if not whitelist:
            blacklist = input("If you wish to blacklist specific countries, enter their country codes separated by spaces. (Press enter to skip): ")

        # Populate the Countries section with out input data
        self.settings.add_section('Countries')
        self.settings.set('Countries', '# simply write country codes separated by spaces e.g. country-blacklist = GB US')
        self.settings.set('Countries', 'country-blacklist', blacklist)
        self.settings.set('Countries', '\n# same as above. If this is non-empty, the blacklist is ignored')
        self.settings.set('Countries', 'country-whitelist', whitelist)

        # Prompt for which categories to enable
        self.settings.add_section('Categories')
        for category in sorted(nordapi.VPN_CATEGORIES.keys()):
            answer = str(utils.input_yes_no("Enable category '%s'?" % category)).lower()
            self.settings.set('Categories', category.replace(' ', '-'), answer)

        self.settings.add_section('Protocols')
        answer = str(utils.input_yes_no("Enable TCP configurations?")).lower()
        self.settings.set('Protocols', 'tcp', answer)
        answer = str(utils.input_yes_no("Enable UDP configurations?")).lower()
        self.settings.set('Protocols', 'udp', answer)

        self.settings.add_section('Benchmarking')
        ping_attempts = input("Input how many ping attempts to make when benchmarking servers (Default: %i attempts): " % self.DEFAULT_PING_ATTEMPTS)
        if not ping_attempts:
            ping_attempts = str(self.DEFAULT_PING_ATTEMPTS)
        self.settings.set('Benchmarking', 'ping-attempts', ping_attempts)

        self.save()  # And save it

    def save(self):
        try:
            with open(self.path, 'w') as settings_file:
                self.settings.write(settings_file)
            utils.chown_path_to_user(self.path)
            self.logger.info("Settings saved successfully.")
            return True
        except Exception as ex:
            self.logger.error(ex)
            return False

    def load(self):
        if os.path.isfile(self.path):
            try:
                self.settings = configparser.ConfigParser(allow_no_value=True, interpolation=None)
                self.settings.read(self.path)
                return True
            except Exception as ex:
                self.logger.error(ex)
        return False

    def get_blacklist(self):
        blacklist = self.settings.get('Countries', 'country-blacklist')
        if blacklist:
            return [code.upper() for code in blacklist.split(' ')]
        else:
            return None

    def get_whitelist(self):
        whitelist = self.settings.get('Countries', 'country-whitelist')
        if whitelist:
            return [code.upper() for code in whitelist.split(' ')]
        else:
            return None

    def get_categories(self):
        categories = []

        for category in nordapi.VPN_CATEGORIES.keys():
            category_name = category.replace(' ', '-')
            if self.settings.getboolean('Categories', category_name):
                categories.append(category)

        return categories

    def get_protocols(self):
        protocols = []

        if self.settings.getboolean('Protocols', 'tcp'):
            protocols.append('tcp')

        if self.settings.getboolean('Protocols', 'udp'):
            protocols.append('udp')

        return protocols

    def get_ping_attempts(self):
        try:
            ping_attempts = int(self.settings.get('Benchmarking', 'ping-attempts'))
            if ping_attempts > 0:  # If ping-attempts is zero or smaller, revert to default
                return ping_attempts
        except Exception:
            pass

        self.logger.warning("Invalid ping-attempts value. Using default value of %d.", self.DEFAULT_PING_ATTEMPTS)
        self.settings.set('Benchmarking', 'ping-attempts', str(self.DEFAULT_PING_ATTEMPTS))  # Lets set the default, so we only get this warning once
        return self.DEFAULT_PING_ATTEMPTS
