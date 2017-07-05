import os
import stat
from io import BytesIO
from zipfile import ZipFile
import subprocess
import logging

logger = logging.getLogger(__name__)


# Since we're running with root priveledges, this will return the current username
def get_current_user():
    return os.getenv("SUDO_USER")


# Change the owner and group of a given path to the current user
def chown_path_to_user(path):
    if os.path.exists(path):
        uid = int(os.getenv('SUDO_UID'))
        gid = int(os.getenv('SUDO_GID'))
        os.chown(path, uid, gid)
        return True
    else:
        return False


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
    """
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode);
    """


def get_rtt_loss(host, ping_attempts):
    output = subprocess.run(['ping', host, '-c', str(ping_attempts)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8')
    output_lines = output.splitlines()

    try:
        split_info = output_lines[-2].split()
        split_rtt = output_lines[-1].split()

        packets_recieved = int(split_info[3])
        if packets_recieved == 0: # If no packets recieved back, return loss of 100% and None as RTT
            return (None, 100)
        else:
            loss = int(split_info[5].split('%')[0])
            avg_rtt = float(split_rtt[3].split('/')[1])
            return (avg_rtt, loss)
    except IndexError as ex:
        print("Could not interpret output of ping command.\nOutput: %s", output)
        return (None, 100)
