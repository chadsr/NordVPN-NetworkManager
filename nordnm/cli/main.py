import click
from nordnm.cli import list, mac, remove, update, add


@click.group()
def cli():
    pass


cli.add_command(list.list_info)
cli.add_command(mac.mac)
cli.add_command(remove.remove)
cli.add_command(update.update)
cli.add_command(add.add)

if __name__ == '__main__':
    cli()
