import click

from nordnm.cli import ensure_sudo
from nordnm.nordmanager import NordNM
from nordnm.settings import SettingsHandler

from nordnm import paths
from nordnm.credentials import CredentialsHandler


@click.group('update')
def update():
    pass


@update.command()
@click.option('--preserve-vpn', is_flag=True, help='whether to preserve current vpn')
def servers(preserve_vpn):
    NordNM().sync(preserve_vpn)


@ensure_sudo
@update.command()
def configs():
    NordNM().download_configs()


@update.command()
def credentials():
    CredentialsHandler(paths.CREDENTIALS).save_new_credentials()


@update.command()
def settings():
    SettingsHandler(paths.SETTINGS).save_new_settings()
