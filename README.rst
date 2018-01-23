NordNM
======

|Build Status| |GitHub tag| |AUR| |license| |GitHub issues|

This tool removes the need for manually handling OpenVPN configurations
from NordVPN. It will synchronise the best servers from chosen countries
into the NetworkManager VPN list. A synchronised VPN can then be chosen
to auto-connect to, whenever NetworkManager brings an network connection
up.

More documentation will be available when nordnm gets to stable
releases.

**Warning:** *This tool is still highly under development. I take no
responsibility for any unforseen problems it may cause.*

**WebRTC warning:** This tool can’t protect against ip leaks through
WebRTC in browsers, more info: `The WebRTC
“bug” <https://www.bestvpn.com/a-complete-guide-to-ip-leaks/#webrtc>`__

Features:
---------

-  Uses the latest NordVPN OpenVPN configuration files.
-  Imports the ‘best’ server of each available type (country, category,
   protocol), based on latency and server load.
-  Provides humanly readable connection names, so you can easily tell
   what each option offers.
-  Provides settings for whitelisting or blacklisting certain countries
   from being synchronised.
-  Automatically adds user credentials to the imported configurations.
-  Tunnels DNS requests through the VPN, to prevent DNS leaks.
-  Disables IPv6 by default, to avoid IPv6 leaks.
-  Set the auto connect server of your choice for all NetworkManager
   connections, instead of per connection. (optional)
-  Set a network kill-switch, to disable the network interface being
   used, if the active VPN disconnects. (optional)
-  Set the NetworkManager MAC address configuration, for simple yet
   powerful control of your MAC address. (optional)

1. Installation
---------------

1.1 Arch (AUR)
~~~~~~~~~~~~~~

Use your preferred method of installing packages via AUR. Any easy
option is to use `yaourt <https://archlinux.fr/yaourt-en>`__:

::

    yaourt -S nordnm

1.2 Debian/Ubuntu
~~~~~~~~~~~~~~~~~

::

    wget -qO - https://bintray.com/user/downloadSubjectPublicKey?username=bintray | sudo apt-key add -
    sudo apt-add-repository "https://dl.bintray.com/chadsr/nordnm-deb main"
    sudo apt update && sudo apt install nordnm

1.3 RPM Based Distributions (Fedora, CentOS, etc)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    wget https://bintray.com/chadsr/nordnm-rpm/rpm -O bintray-chadsr-nordnm-rpm.repo
    sudo mv bintray-chadsr-nordnm-rpm.repo /etc/yum.repos.d/
    sudo yum install nordnm

1.4 Python PIP
~~~~~~~~~~~~~~

**Note:** If you install via PIP, system dependencies will need to be
installed manually. It is therefore recommended to install via your
system package manager. If your system is not yet listed above, leave an
issue and it can be added ASAP.

*If your default Python version is 2.x, you will need to use pip3 below*

System Install
^^^^^^^^^^^^^^

::

    sudo -H pip install nordnm

User Install
^^^^^^^^^^^^

::

    pip install --user nordnm

2. Usage
--------

**Note:** Many of the commands below can be chained into one line. A
recommended example of this is to synchronise, update configuration
files and set any auto-connect/kill-switch at the same time.

For example:

::

    sudo nordnm s -uka nl normal tcp

::

    usage: nordnm [-h] [-k] [-a [COUNTRY_CODE] [VPN_CATEGORY] [PROTOCOL]]  ...

    optional arguments:
      -h, --help            show this help message and exit
      -k, --kill-switch     Sets a network kill-switch, to disable the active
                            network interface when an active VPN connection
                            disconnects.
      -a [COUNTRY_CODE] [VPN_CATEGORY] [PROTOCOL], --auto-connect [COUNTRY_CODE] [VPN_CATEGORY] [PROTOCOL]
                            Configure NetworkManager to auto-connect to the chosen
                            server type. Takes country code, category and
                            protocol.

    commands:
                            Each command has its own help page, which can be
                            accessed via nordnm <COMMAND> --help
        remove (r)          Remove either active connections, auto-connect, kill-
                            switch, data or all.
        update (u)          Update a specified setting.
        list (l)            List the specified information.
        sync (s)            Synchronise the optimal servers (based on load and
                            latency) to NetworkManager.
        mac (m)             Global NetworkManager MAC address preferences. This
                            command will affect ALL NetworkManager connections
                            permanently.

Suggestions/Bugs
----------------

If you have any feature suggestions or find an interesting bug, please
let me know. More intuitive options and fixes will be coming in the
future.

.. |Build Status| image:: https://travis-ci.org/Chadsr/NordVPN-NetworkManager.svg?branch=master
   :target: https://travis-ci.org/Chadsr/NordVPN-NetworkManager
.. |GitHub tag| image:: https://img.shields.io/github/tag/Chadsr/NordVPN-NetworkManager.svg
   :target: https://github.com/Chadsr/NordVPN-NetworkManager/releases
.. |AUR| image:: https://img.shields.io/aur/version/nordnm.svg
   :target: https://aur.archlinux.org/packages/nordnm/
.. |license| image:: https://img.shields.io/github/license/Chadsr/NordVPN-NetworkManager.svg
   :target: https://github.com/Chadsr/NordVPN-NetworkManager/blob/master/LICENSE
.. |GitHub issues| image:: https://img.shields.io/github/issues/Chadsr/NordVPN-NetworkManager.svg
   :target: https://github.com/Chadsr/NordVPN-NetworkManager/issues
