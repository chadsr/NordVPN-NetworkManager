from setuptools import setup
import sys
from nordnm import __version__, __license__, __package__

# Minimal version numbers
PYTHON_VERSION = 3
PYTHON_SUBVERSION = 5

if sys.version_info < (PYTHON_VERSION, PYTHON_SUBVERSION):
    sys.exit("Error: %s requires Python %i.%i or greater to be installed. Please use a pip corresponding to this version or greater." % (__package__, PYTHON_VERSION, PYTHON_SUBVERSION))


def get_readme():
    with open('README.rst', encoding='utf-8') as f:
        readme = f.read()
        f.close()

    return readme


def get_requirements():
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    return requirements


setup(
    name=__package__,
    version=__version__,
    author='Ross Chadwick',
    author_email='ross@rchadwick.co.uk',
    packages=[__package__],
    url='https://github.com/Chadsr/NordVPN-NetworkManager',
    license=__license__,
    description='A CLI tool for automating the importing, securing and usage of NordVPN OpenVPN servers through NetworkManager.',
    long_description=get_readme(),
    install_requires=get_requirements(),
    platforms=['GNU/Linux', 'Ubuntu', 'Debian', 'Kali', 'CentOS', 'Arch', 'Fedora'],
    zip_safe=False,
    keywords=['openvpn', 'nordvpn', 'networkmanager', 'network-manager', 'vpn'],
    entry_points={
        'console_scripts': [
            'nordnm = nordnm.__main__:main'
        ]},
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'Topic :: Internet',
        'Topic :: Desktop Environment :: Gnome',
        'Topic :: Utilities',
        'Topic :: Security',
        'Topic :: System :: Networking',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
