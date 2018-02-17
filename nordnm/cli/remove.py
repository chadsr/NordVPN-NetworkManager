import click
from nordnm import networkmanager
from nordnm.nordmanager import NordNM


@click.group('remove')
def remove():
    pass


@remove.command('all')
def remove_all():
    pass


@remove.command('mac')
def remove_mac():
    networkmanager.remove_global_mac_address()


@remove.command('connections')
def remove_connections():
    NordNM.remove_active_connections()
    networkmanager.remove_dns_resolv()


@remove.command('auto-connect')
def remove_auto_connect():
    networkmanager.remove_autoconnect()


@remove.command('data')
def remove_data():
    pass

