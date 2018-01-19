from nordnm import utils
from nordnm import nordapi

import configparser
import logging
import getpass
import os


class CredentialsHandler(object):
    SECTION_TITLE = 'NordVPN Credentials'

    def __init__(self, path):
        self.logger = logging.getLogger(__name__)

        self.path = path
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
        username = self.config.get(self.SECTION_TITLE, 'username')
        if username:
            return username
        else:
            return None

    def get_password(self):
        password = self.config.get(self.SECTION_TITLE, 'password')
        if password:
            return password
        else:
            return None

    def save_new_credentials(self):
        valid = False

        print("\nPlease input your NordVPN credentials:")

        while not valid:
            username = input("Email: ")
            password = getpass.getpass("Password: ")

            if username and password:
                self.logger.info("Attempting to verify credentials...")
                if nordapi.verify_user_credentials(username, password):
                    valid = True
                else:
                    self.logger.error("The provided credentials could not be verified. Try entering them again and checking your Internet connectivity.")

        if not self.config.has_section(self.SECTION_TITLE):
            self.config.add_section(self.SECTION_TITLE)

        self.config.set(self.SECTION_TITLE, 'username', username)
        self.config.set(self.SECTION_TITLE, 'password', password)
        self.save()
        self.logger.info("New credentials saved successfully!")
