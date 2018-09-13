from nordnm import utils
from nordnm.vpn_provider import VPNProvider

import configparser
import logging
import getpass
import os


class CredentialsHandler(object):

    def __init__(self, path: str, provider: VPNProvider):
        self.logger = logging.getLogger(__name__)

        self.path = path
        self.provider = provider
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=None)

        if not self.load():
            self.logger.warning("No credentials found!")
            self.save_new_credentials()  # Prompt for credentials

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

    def get_username(self):
        username = self.config.get(self.provider.name, 'username')
        if username:
            return username
        else:
            return None

    def get_password(self):
        password = self.config.get(self.provider.name, 'password')
        if password:
            return password
        else:
            return None

    def save_new_credentials(self):
        valid = False

        print("\nPlease input your %s credentials:" % self.provider.name)

        while not valid:
            username = input("Email: ")
            password = getpass.getpass("Password: ")

            if username and password:
                self.logger.info("Attempting to verify credentials...")
                if self.provider.verify_user_credentials(username, password):
                    valid = True
                else:
                    self.logger.error("The provided credentials could not be verified. Try entering them again and checking your Internet connectivity.")

        if not self.config.has_section(self.provider.name):
            self.config.add_section(self.provider.name)

        self.config.set(self.provider.name, 'username', username)
        self.config.set(self.provider.name, 'password', password)
        self.save()
        self.logger.info("New credentials saved successfully!")
