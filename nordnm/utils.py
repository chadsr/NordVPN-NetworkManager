import os
import stat
from io import BytesIO
from zipfile import ZipFile
import subprocess
import logging
import getpass
import requests

logger = logging.getLogger(__name__)


def get_pypi_package_version(package_name):
    try:
        resp = requests.get("https://pypi.python.org/pypi/" + package_name + "/json", timeout=0.1)

        if resp.status_code == requests.codes.ok:
            package = resp.json()

            if 'version' in package['info']:
                return package['info']['version']

    except Exception as ex:
        logger.error("Could not check PyPi for latest version.")

    return False


# Yes/No question, defaults to yes
def input_yes_no(question):
    yes = set(['yes', 'y', ''])
    no = set(['no', 'n'])

    while True:
        choice = input(question + " (y/n): ").lower()
        if choice in yes:
            return True
        elif choice in no:
            return False


# Since we're running with root priveledges, this will return the current username
def get_current_user():
    username = os.getenv("SUDO_USER")
    if not username:
        username = str(getpass.getuser())

    return username


# Change the owner and group of a given path to the current user
def chown_path_to_user(path):
    if os.path.exists(path):
        uid = int(os.getenv('SUDO_UID'))
        gid = int(os.getenv('SUDO_GID'))
        os.chown(path, uid, gid)
        return True
    else:
        return False


def format_std_string(input_string):
    return input_string.decode('utf-8').replace('\n', ' ')


def extract_zip(input_stream, output_path, chown_to_user=True):
    try:
        zipfile = ZipFile(BytesIO(input_stream))
        zipfile.extractall(output_path)
        file_list = zipfile.namelist()

        if chown_to_user:
            # chown the extracted files to the current user, instead of root
            for file_name in file_list:
                file_path = os.path.join(output_path, file_name)
                chown_path_to_user(file_path)
        return True

    except Exception as ex:
        logger.error(ex)
        return False


def make_executable(file_path):
    try:
        if os.path.isfile(file_path):
            st = os.stat(file_path)
            os.chmod(file_path, st.st_mode | stat.S_IEXEC)
            return True

    except Exception as ex:
        logger.error(ex)
        return False


def get_rtt_loss(host, ping_attempts):
    try:
        output = subprocess.run(['ping', '-c', str(ping_attempts), '-n', '-i', '0.2', '-W', '1', host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output.check_returncode()

        lines = output.stdout.decode('utf-8').splitlines()

        split_info = lines[-2].split()
        split_rtt = lines[-1].split()

        packets_recieved = int(split_info[3])
        if packets_recieved > 0:
            loss = float(split_info[5].split('%')[0])
            avg_rtt = float(split_rtt[3].split('/')[1])
            return (avg_rtt, loss)

    except IndexError as ex:
        logger.error("Could not interpret output of ping command.\nOutput: %s", ex)

    except subprocess.CalledProcessError:
        err = format_std_string(output.stderr)
        if err:
            logger.error("Ping failed with error: %s", err)
        # else:
        #    out = format_std_string(output.stdout)
        #    logger.warning("Ping failed with output: %s", out)

    return (None, 100)  # If anything failed, return rtt as None and 100% loss
