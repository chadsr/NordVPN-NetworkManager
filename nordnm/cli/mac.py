import click


@click.command()
@click.option('--random', '-r', is_flag=True,
              help='A randomised MAC addresss will be generated on each connect')
@click.option('--stable', '-s', is_flag=True,
              help='Use stable, hashed MAC address on connect')
@click.option('--preserve', is_flag=True,
              help='Don\'t change the current MAC address upon connection')
@click.option('--permanent', is_flag=True,
              help='Use the permanent MAC address of the device on connection')
@click.option('--explicit', '-e', 'mac_address',
              help='Specify a MAC address to use on connection')
def mac(random, stable, preserve, permanent, mac_address):
    print(random, stable, preserve, permanent, mac_address)
    pass
