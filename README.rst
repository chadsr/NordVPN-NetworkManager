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

**Warning:** *This tool is still highly under development and is not yet
robust enough to use reliably. I take no responsibility for any
unforseen problems it may cause.*

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

1. Requirements
---------------

Debian/Ubuntu
~~~~~~~~~~~~~

::

    sudo apt update && sudo apt install openvpn network-manager network-manager-gnome network-manager-openvpn-gnome

Arch
~~~~

::

    sudo pacman -S networkmanager openvpn networkmanager-openvpn

2. Installation
---------------

**Please note:** This tool requires Python 3.5 or later. (May change in
the future)

::

    sudo -H pip3 install nordnm

3. Usage
--------

Setup/Update Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    sudo nordnm --update

This will download the latest openvpn configuration files, prompt you
for your account credentials and also create a settings file
($HOME/.nordnm/settings.conf). Currently, you will need to manually edit
the settings file with your desired configuration.

If you experience connections failing, you may want to run the update
parameter again, since the configuration files may have been updated.

Synchronising
~~~~~~~~~~~~~

::

    sudo nordnm --sync

This option will use your current settings to find the best server for
each country, category and protocol combination that you have enabled.
The configurations will then be added to NetworkManager automatically,
ready to use.

Auto-Connect to a Server
~~~~~~~~~~~~~~~~~~~~~~~~

::

    sudo nordnm --auto-connect <country_code> <category> <protocol>

Auto-connect allows you to choose a server from your already
synchronised configurations to automatically connect to whenever an
Internet enabled network interface (e.g. wifi/ethernet) connects to a
network.

Remove All Connections
~~~~~~~~~~~~~~~~~~~~~~

::

    sudo nordnm --purge

Removes all of the synchronised VPN configurations from NetworkManager
and any enabled auto-connection setup.

Update Credentials
~~~~~~~~~~~~~~~~~~

::

    sudo nordnm --credentials

Allows you to re-enter your account credentials via the terminal,
instead of editing files manually.

Update Settings
~~~~~~~~~~~~~~~

::

    sudo nordnm --settings

Allows you to re-enter synchronisation settings.

Help
~~~~

::

    sudo nordnm --help

Simply display all the options above with a short description.

Suggestions/Bugs
----------------

If you have any feature suggestions or find an interesting bug, please
let me know. More intuitive options and fixes will be coming in the
future.

.. |Build Status| image:: https://travis-ci.org/Chadsr/NordVPN-NetworkManager.svg?branch=master
   :target: https://travis-ci.org/Chadsr/NordVPN-NetworkManager
