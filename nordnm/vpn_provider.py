from abc import ABC, abstractmethod


class VPNServer(object):
    def __init__(self, domain, address, load):
        self.domain = domain
        self.address = address
        self.load = load


class VPNProvider(ABC):
    @abstractmethod
    @staticmethod
    def get_servers(country_code: str, category: str, protocol: str, limit: int) -> list:
        """
        Arguments:
            country_code: A two-character, lower-case country code e.g. 'us'
            category: An internal category name
            protocol: An internal protocol NAME
            limit: The maximum number of servers to return

        Output:
            [
                VPNServer(),
                ...
            ]
        """

    @abstractmethod
    @staticmethod
    def get_nameservers(host: str) -> list:
        ...

    @abstractmethod
    @staticmethod
    def get_configuration_files(etag: str) -> bin:
        ...

    @abstractmethod
    @staticmethod
    def get_available_countries() -> dict:
        ...

    @abstractmethod
    @staticmethod
    def get_available_categories() -> dict:
        ...

    @abstractmethod
    @staticmethod
    def get_available_protocols() -> dict:
        ...

    @abstractmethod
    @staticmethod
    def verify_user_credentials(username: str, password: str) -> bool:
        ...
