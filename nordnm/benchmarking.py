from nordnm import nordnm
from nordnm import utils
from nordnm import nordapi

import multiprocessing
from functools import partial
import numpy
import os
import sys
import subprocess
from decimal import Decimal
import resource

EXP_SENSITIVITY = 50  # Controls the gradient of the exponential score function. The higher the number, the smaller the gradient (change)
MAX_FD = 512


def get_server_score(server, ping_attempts):
    load = server['load']
    ip_addr = server['ip_address']

    score = 0  # Lowest starting score
    rtt = None

    # If a server is at 95% load or greater, we don't need to waste time pinging. Just keep starting score.
    if load < 95:
        rtt, loss = utils.get_rtt_loss(ip_addr, ping_attempts)

        if loss < 5:  # Similarly, if packet loss is >= 5%, the connection is not reliable. Keep the starting score.
            score = round(Decimal(1 / (numpy.exp(((load/100) * rtt) / EXP_SENSITIVITY))), 4)  # Maximise the score for smaller values of ln(load + rtt)

    return (score, load, rtt)


def compare_server(server, best_servers, ping_attempts, valid_protocols, valid_categories):
    supported_protocols = []
    if server['features']['openvpn_udp'] and 'udp' in valid_protocols:
        supported_protocols.append('udp')
    if server['features']['openvpn_tcp'] and 'tcp' in valid_protocols:
        supported_protocols.append('tcp')

    country_code = server['flag'].lower()
    domain = server['domain']
    score, load, latency = get_server_score(server, ping_attempts)

    # The ping benchmark failed, so return fail
    if not latency:
        return False

    for category in server['categories']:
        category_long_name = category['name']
        if category_long_name in valid_categories:
            category_short_name = nordapi.VPN_CATEGORIES[category['name']]

            for protocol in supported_protocols:
                best_score = -1

                if best_servers.get((country_code, category_short_name, protocol)):
                    best_score = best_servers[country_code, category_short_name, protocol]['score']

                if score > best_score:
                    name = nordnm.generate_connection_name(server, protocol)
                    best_servers[country_code, category_short_name, protocol] = {'name': name, 'domain': domain, 'score': score, 'load': load, 'latency': latency}

    return True


def get_num_processes(num_servers):
    # Since each process is not resource heavy and simply takes time waiting for pings, maximise the number of processes (within constraints of the current configuration)

    # Maximum open file descriptors of current configuration
    soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)

    # Find how many file descriptors are already in use by the parent process
    ppid = os.getppid()
    used_file_descriptors = int(subprocess.run('ls -l /proc/' + str(ppid) + '/fd | wc -l', shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8'))

    # Max processes is the number of file descriptors left, before the soft limit (configuration maximum) is reached
    max_processes = int((soft_limit - used_file_descriptors))

    # If the number of free file descriptors is larger than our defined max, the cap it at that
    if max_processes > MAX_FD:
        max_processes = MAX_FD

    if num_servers > max_processes:
        return max_processes
    else:
        return num_servers


def get_best_servers(server_list, ping_attempts, valid_protocols, valid_categories, slow_mode=False):
    manager = multiprocessing.Manager()
    best_servers = manager.dict()

    num_servers = len(server_list)

    if slow_mode:
        num_processes = multiprocessing.cpu_count()
    else:
        num_processes = get_num_processes(num_servers)

    pool = multiprocessing.Pool(num_processes, maxtasksperchild=1)

    results = []
    for i, result in enumerate(pool.imap(partial(compare_server, best_servers=best_servers, ping_attempts=ping_attempts, valid_protocols=valid_protocols, valid_categories=valid_categories), server_list)):
        sys.stderr.write("\r[INFO] %i/%i benchmarks finished." % (i + 1, num_servers))
        results.append(result)

    sys.stderr.write('\n')

    pool.close()

    num_success = results.count(True)

    return (best_servers, num_success)
