import os
import stat
from io import BytesIO
from zipfile import ZipFile
import subprocess
import logging
import getpass
import requests

logger = logging.getLogger(__name__)


class LoggingFormatter(logging.Formatter):
    info_format = "[%(levelname)s] %(message)s"
    error_format = "[%(levelname)s] [%(name)s.%(funcName)s:%(lineno)d] %(message)s"

    def __init__(self):
        super().__init__(fmt=self.info_format, datefmt=None, style='%')

    def format(self, record):
        # Save the current format so we can restore it later
        default_fmt = self._style._fmt

        if record.levelno == logging.ERROR:
            self._style._fmt = self.error_format
        else:
            self._style._fmt = self.info_format

        # Call the original class to do the actual logging
        result = logging.Formatter.format(self, record)

        # Restore the default format
        self._fmt = default_fmt

        return result


def get_pypi_package_version(package_name):
    try:
        resp = requests.get("https://pypi.python.org/pypi/" + package_name +
                            "/json",
                            timeout=0.1)

        if resp.status_code == requests.codes.ok:
            package = resp.json()

            if 'version' in package['info']:
                return package['info']['version']

    except Exception:
        logger.warning("Could not check for latest version.")

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


# Returns the process back to root user to run a given function, then back to normal user
def run_as_root(method):
    os.seteuid(0)  # Be root
    result = method()
    os.seteuid(int(os.getenv("SUDO_UID")))

    return result


# Since we're running with root priveledges, this will return the current username
def get_current_user():
    username = os.getenv("SUDO_USER")
    if not username:
        username = str(getpass.getuser())

    return username


def format_std_string(input_string):
    return input_string.decode('utf-8').replace('\n', ' ')


def extract_zip(input_stream, output_path):
    try:
        zipfile = ZipFile(BytesIO(input_stream))
        zipfile.extractall(output_path)

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
        ping_env = os.environ.copy()
        ping_env["LANG"] = "C"
        output = subprocess.run([
            'ping', '-c', str(ping_attempts),
            '-n', '-i', '0.2', '-W', '1', host
        ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=ping_env)
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
        logger.error("Could not interpret output of ping command.\nOutput: %s",
                     ex)

    except subprocess.CalledProcessError:
        err = format_std_string(output.stderr)
        if err:
            logger.error("Ping failed with error: %s", err)
        # else:
        #    out = format_std_string(output.stdout)
        #    logger.warning("Ping failed with output: %s", out)

    return (None, 100)  # If anything failed, return rtt as None and 100% loss
