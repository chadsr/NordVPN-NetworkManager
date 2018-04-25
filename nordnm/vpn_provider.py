from abc import ABC, abstractmethod


class VPNProvider(ABC):
    @abstractmethod
    @staticmethod
    def get_servers(country_code: str, category: str, protocol: str, limit: int):
        ...

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
