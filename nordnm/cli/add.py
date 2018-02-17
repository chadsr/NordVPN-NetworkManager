import click

from nordnm.nordmanager import NordNM


@click.command('add')
@click.argument('country_code')
@click.argument('vpn_category', default='normal')
@click.argument('protocol', default='tcp')
def add(country_code, vpn_category, protocol):
    nordnm = NordNM()
    nordnm.enable_auto_connect(country_code=country_code, category=vpn_category, protocol=protocol)


if __name__ == '__main__':
    nordnm = NordNM()
