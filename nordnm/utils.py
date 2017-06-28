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


def get_rtt(host, ping_attempts):
    output = subprocess.run(['fping', host, '-c', str(ping_attempts)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8')
    loss = int(output.strip().split('/')[4].split('%')[0])  # percentage loss
    if loss < 100:
        avg_rtt = output.split()[-1].split('/')[1]
        return round(float(avg_rtt), 2)
    else:
        return 99999
