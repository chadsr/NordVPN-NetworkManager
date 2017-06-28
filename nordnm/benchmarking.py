import utils
import nordapi

import multiprocessing
from functools import partial
import resource


def generate_connection_name(server, protocol):
    short_name = server['domain'].split('.')[0]
    connection_name = short_name + '.' + protocol + '['

    for i, category in enumerate(server['categories']):
        category_name = nordapi.VPN_CATEGORIES[category['name']]
        if i > 0:  # prepend a separator if there is more than one category
            category_name = '|' + category_name

        connection_name = connection_name + category_name

    return connection_name + ']'


def get_server_score(server, ping_attempts):
    load = server['load']
    domain = server['domain']
    rtt = utils.get_rtt(domain, ping_attempts)
    score = int((1/(rtt*load+1)*1000))  # TODO: Improve scoring function
    return score


def compare_server(server, best_servers, ping_attempts):
    supported_protocols = []
    if server['features']['openvpn_udp']:
        supported_protocols.append('udp')
    if server['features']['openvpn_tcp']:
        supported_protocols.append('tcp')

    country_code = server['flag']
    domain = server['domain']
    score = get_server_score(server, ping_attempts)

    for category in server['categories']:
        category_name = nordapi.VPN_CATEGORIES[category['name']]

        for protocol in supported_protocols:
            best_score = 0

            if best_servers.get((country_code, category_name, protocol)):
                best_score = best_servers[country_code, category_name, protocol]['score']

            if score > best_score:
                name = generate_connection_name(server, protocol)
                best_servers[country_code, category_name, protocol] = {'name': name, 'domain': domain, 'score': score}


def get_num_processes(num_servers):
    # Since each process is not resource heavy and simply takes time waiting for pings, maximise the number of processes (within constraints of the current configuration)
    soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    max_processes = int(soft_limit/multiprocessing.cpu_count())  # This doesn't particularly make sense right now...

    if num_servers > max_processes:
        return max_processes
    else:
        return num_servers


def get_best_servers(server_list, ping_attempts):
    manager = multiprocessing.Manager()
    best_servers = manager.dict()

    num_servers = len(server_list)
    num_processes = get_num_processes(num_servers)

    pool = multiprocessing.Pool(num_processes)
    pool.map(partial(compare_server, best_servers=best_servers, ping_attempts=ping_attempts), server_list)
    pool.close()

    return best_servers
