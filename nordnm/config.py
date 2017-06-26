import utils

import configparser
import logging
import os

class ConfigHandler(object):
    DEFAULT_PING_ATTEMPTS = 3

    def __init__(self, path):
        self.logger = logging.getLogger(__name__)

        self.path = path
        self.config = configparser.ConfigParser(allow_no_value=True)

        if self.load():  # If we successfully load an existing config
            self.logger.info("Existing configuration loaded.")
        else:
            self.logger.warning("No existing configuration found. Saving default settings.")
            # Generate default config
            self.config.add_section('General')
            self.config.set('General', '# simply write country codes separated by spaces e.g. country-blacklist = GB US')
            self.config.set('General', 'country-blacklist', '')
            self.config.set('General', '\n# same as above. If this is non-empty, the blacklist is ignored')
            self.config.set('General', 'country-whitelist', '')

            self.config.add_section('Benchmarking')
            self.config.set('Benchmarking', 'ping-attempts', str(self.DEFAULT_PING_ATTEMPTS))

            self.save()  # And save it

    def save(self):
        try:
            with open(self.path, 'w') as config_file:
                self.config.write(config_file)
            utils.chown_path_to_user(self.path)
            return True
        except Exception as ex:
            self.logger.error(ex)
            return False

    def load(self):
        if os.path.isfile(self.path):
            try:
                self.config.read(self.path)
                return True
            except Exception as ex:
                self.logger.error(ex)
        return False

    def get_blacklist(self):
        blacklist = self.config.get('General', 'country-blacklist')
        if blacklist:
            return [code.upper() for code in blacklist.split(' ')]
        else:
            return None

    def get_whitelist(self):
        whitelist = self.config.get('General', 'country-whitelist')
        if whitelist:
            return [code.upper() for code in whitelist.split(' ')]
        else:
            return None

    def get_ping_attempts(self):
        try:
            ping_attempts = int(self.config.get('Benchmarking', 'ping-attempts'))
            if ping_attempts > 0: # If ping-attempts is zero or smaller, revert to default
                return ping_attempts
        except:
            pass

        self.logger.warning("Invalid ping-attempts value. Using default value of %d.", self.DEFAULT_PING_ATTEMPTS)
        self.config.set('Benchmarking', 'ping-attempts', str(self.DEFAULT_PING_ATTEMPTS)) # Lets set the default, so we only get this warning once
        return self.DEFAULT_PING_ATTEMPTS
