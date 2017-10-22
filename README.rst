NordNM
======

|Build Status|

This tool removes the need for manually handling OpenVPN configurations
from NordVPN. It will synchronise the best servers from chosen countries
into the NetworkManager VPN list. A synchronised VPN can then be chosen
to auto-connect to, whenever NetworkManager brings an network connection
up.

More documentation will be available when this tool is out of Alpha
releases.

**Warning:** *This tool is still highly under development. I take no
responsibility for any unforseen problems it may cause.*

Features:
---------

-  Uses the latest NordVPN OpenVPN configuration files.
-  Imports the 'best' server of each available type (country, category,
   protocol), based on latency and server load.
-  Provides humanly readable connection names, so you can easily tell
   what each option offers.
-  Provides settings for whitelisting or blacklisting certain countries
   from being synchronised.
-  Automatically adds user credentials to the imported configurations.
-  Uses the NordVPN DNS servers to prevent DNS request leaks.
-  Disables IPv6 by default, to avoid IPv6 leaks.
-  Sets the auto connect server of your choice for all NetworkManager
   connections, instead of per connection. (optional)
-  Sets a network kill-switch, to disable the network interface being
   used, if the active VPN disconnects. (optional)

1. Requirements
---------------

Debian/Ubuntu
~~~~~~~~~~~~~

::

    sudo apt update && sudo apt install network-manager openvpn network-manager-openvpn-gnome

Arch
~~~~

::

    sudo pacman -S --needed networkmanager openvpn networkmanager-openvpn

2. Installation
---------------

**Please note:** This tool requires Python 3.5 or later. (May change in
the future)

*If your default Python version is 2.x, you will need to use pip3 below*

System Install
~~~~~~~~~~~~~~

::

    sudo -H pip install nordnm

User Install
~~~~~~~~~~~~

::

    pip install --user nordnm

3. Usage
--------

**Note:** Many of the commands below can be chained into one line. A
recommended example of this is to update, synchronise and set any
auto-connect/kill-switch at the same time.

For example:

::

    sudo nordnm -uska nl normal tcp

::

    usage: nordnm [-h] [-u] [-s] [-a [COUNTRY_CODE] [VPN_CATEGORY] [PROTOCOL]]
                  [-k] [-p] [--countries] [--categories] [--credentials]
                  [--settings]

    optional arguments:
      -h, --help            show this help message and exit
      -u, --update          Download the latest OpenVPN configurations from
                            NordVPN
      -s, --sync            Synchronise the optimal servers (based on load and
                            latency) to NetworkManager
      -a [COUNTRY_CODE] [VPN_CATEGORY] [PROTOCOL], --auto-connect [COUNTRY_CODE] [VPN_CATEGORY] [PROTOCOL]
                            Configure NetworkManager to auto-connect to the chosen
                            server type. Takes country code, category and protocol
      -k, --kill-switch     Sets a network kill-switch, to disable the active
                            network interface when an active VPN connection
                            disconnects
      -p, --purge           Remove all active connections, auto-connect and kill-
                            switch (if configured)
      --countries           Display a list of the available countries
      --categories          Display a list of the available VPN categories
      --credentials         Change the existing saved credentials
      --settings            Change the existing saved settings

Suggestions/Bugs
----------------

If you have any feature suggestions or find an interesting bug, please
let me know. More intuitive options and fixes will be coming in the
future.

.. |Build Status| image:: https://travis-ci.org/Chadsr/NordVPN-NetworkManager.svg?branch=master
   :target: https://travis-ci.org/Chadsr/NordVPN-NetworkManager
