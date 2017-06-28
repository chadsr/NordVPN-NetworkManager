import configparser
import logging
import getpass
import os


class CredentialsHandler(object):
    SECTION_TITLE = 'NordVPN Credentials'

    def __init__(self, path):
        self.logger = logging.getLogger(__name__)

        self.path = path
        self.config = configparser.ConfigParser(allow_no_value=True)

        if self.load():
            self.logger.info("Existing credentials loaded.")
        else:
            self.logger.info("No credentials found. Please input below:")
            self.save_new_credentials()

    def save(self):
        try:
            with open(self.path, 'w') as config_file:
                self.config.write(config_file)
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
        username = None
        password = None

        while not username and not password:
            username = input("Username: ")
            password = getpass.getpass("Password: ")

        self.config.add_section(self.SECTION_TITLE)
        self.config.set(self.SECTION_TITLE, 'username', username)
        self.config.set(self.SECTION_TITLE, 'password', password)
        self.save()
