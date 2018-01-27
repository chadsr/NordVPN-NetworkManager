NordNM
======

|Build Status| |GitHub tag| |AUR| |license| |GitHub issues|

This tool **automates** the importing and **secures** the usage of
NordVPN OpenVPN configurations through Network Manager.

**WebRTC Privacy Warning:** This tool can’t protect against IP leaks
through WebRTC in browsers. For more information: `The WebRTC
“bug” <https://www.bestvpn.com/a-complete-guide-to-ip-leaks/#webrtc>`__

Features:
---------

If you encounter a **problem** or have a **feature request**, please
make an issue report and it will be looked into ASAP.

-  **Small Footprint:** Nordnm does not use any background processes.
   Once a synchronise has finished, it’s all handled by Network Manager.
-  **Improved readability:** Humanly readable connection names, so you
   can easily tell what each connection offers.
-  **Only import what you need:** Your preference of countries, VPN
   categories and protocols can be saved, to synchronise only the
   options you need.
-  **Always up-to-date:** The tool can be configured to always check if
   it is using the latest NordVPN OpenVPN configuration files.
-  **Server Benchmarking:** Servers are benchmarked according to their
   latency and server load, to determine the “best” options available.
-  **Auto-Connect:** A server of your choice can be set to automatically
   activate whenever you connect to the Internet.
-  **DNS Tunnelling:** DNS requests are forced to go through the VPN
   tunnel, to prevent privacy ruining `DNS
   leaks <https://en.wikipedia.org/wiki/DNS_leak>`__.
-  **IPv6 Disabled:** IPv6 is disabled by default, to avoid IPv6 leaks.
-  **Kill-Switch:** Set a network kill-switch, to disable the network
   interface being used if the active VPN disconnects.
-  **MAC Address Manipulation:** Change the MAC address used by Network
   Manager in a variety of ways (randomization, spoofing, etc), to avoid
   tracking across networks.

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

**Note:** Each command has its own help section, which can be acccessed
via ``nordnm <COMMAND> --help``.

2.1 Example Usage
~~~~~~~~~~~~~~~~~

-  **View available categories and countries:**

::

    sudo nordnm list --categories --countries

-  **Synchronise, update configuration files, activate the kill-switch
   and auto-connect to a “normal” UDP server in the US:**

::

    sudo nordnm sync -uka us normal udp

-  **View metrics of the synchronised servers:**

::

    sudo nordnm list --active-servers

-  **Set your MAC address to be randomised each time you connect to a
   network:**

::

    sudo nordnm mac --random

-  **Change the auto-connect to another synchronised server:**

::

    sudo nordnm -a ru p2p udp

-  **Update the settings:**

::

    sudo nordnm update --settings

-  **Update the user credentials:**

::

    sudo nordnm update --credentials

-  **Disable the network kill-switch:**

::

    sudo nordnm remove --kill-switch

-  **Remove all settings and files:**

::

    sudo nordnm remove --all

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
