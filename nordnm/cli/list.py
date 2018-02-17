import pickle

import click
import os

from nordnm import nordapi, paths, log


@click.group('list')
def list_info():
    pass


@list_info.command('countries')
def list_countries():
    servers = nordapi.get_server_list(sort_by_country=True)
    if servers:
        format_string = "| {:22} | {:4} |".format
        countries = []

        print("\n Note: You must use the country code, NOT the country name in this tool.\n")
        print(format_string("NAME", "CODE"))
        print("|------------------------+------|")

        for server in servers:
            country_code = server['flag']
            if country_code not in countries:
                countries.append(country_code)
                country_name = server['country']
                print(format_string(country_name, country_code))
        print()  # For spacing
    else:
        log.error("Could not get available countries from the NordVPN API.")


@list_info.command('categories')
def list_categories():
    format_string = "| {:<10} | {:20} |".format
    print("\n Note: You must use the short name in this tool.\n")
    print(format_string("SHORT NAME", "LONG NAME"))
    print("|------------+----------------------|")
    for long_name, short_name in nordapi.VPN_CATEGORIES.items():
        print(format_string(short_name, long_name))
    print()  # For spacing


def _get_active_users():
    # todo
    if os.path.isfile(paths.ACTIVE_SERVERS):
        try:
            with open(paths.ACTIVE_SERVERS, 'rb') as fp:
                return pickle.load(fp)
        except Exception as ex:
            log.error(ex)
            return None


@list_info.command('active-users')
def list_active_users():
    active_servers = _get_active_users()
    printed_servers = []
    if active_servers:
        print("Note: All metrics below are from the last synchronise.\n")
        format_string = "| {:20} | {:8} | {:11} | {:8} |".format
        print(format_string("NAME", "LOAD (%)", "LATENCY (s)", "SCORE"))
        print("|----------------------+----------+-------------+----------|")

        for params in active_servers:
            name = active_servers[params]['domain']
            if name not in printed_servers:
                printed_servers.append(name)
                score = active_servers[params]['score']
                load = active_servers[params]['load']
                latency = round(active_servers[params]['latency'], 2)
                print(format_string(name, load, latency, score))
        print()  # For spacing
    else:
        log.warning("No active servers to display.")
