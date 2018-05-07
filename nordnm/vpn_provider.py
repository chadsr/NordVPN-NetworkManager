from abc import ABC, abstractmethod
from typing import Union


class VPNServer(object):
    def __init__(self, domain, address, load):
        self.domain = domain
        self.address = address
        self.load = load


class VPNProvider(ABC):
    @staticmethod
    @abstractmethod
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

    @staticmethod
    @abstractmethod
    def get_nameservers(host: str) -> list:
        ...

    @staticmethod
    @abstractmethod
    def get_configuration_files(etag: Union[str, None]) -> bin:
        ...

    @staticmethod
    @abstractmethod
    def get_available_countries() -> dict:
        ...

    @staticmethod
    @abstractmethod
    def get_available_categories() -> dict:
        ...

    @staticmethod
    @abstractmethod
    def get_available_protocols() -> dict:
        ...

    @staticmethod
    @abstractmethod
    def verify_user_credentials(username: str, password: str) -> bool:
        ...
