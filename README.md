# NordNM

This tool removes the need for manually handling OpenVPN configurations from NordVPN. It will synchronise the best servers from chosen countries into the NetworkManager VPN list. A synchronised VPN can then be chosen to auto-connect to, whenever NetworkManager brings an network connection up.

More documentation will be available when this tool is out of Alpha releases.

**Warning:**
*This tool is still highly under development and is not yet robust enough to use reliably. I take no responsibility for any unforseen problems it may cause.*

## Features:
- Uses the latest NordVPN OpenVPN configuration files.
- Imports the 'best' server of each available type (country, category, protocol), based on latency and server load.
- Provides humanly readable connection names, so you can easily tell what each option offers.
- Provides settings for whitelisting or blacklisting certain countries from being synchronised.
- Automatically adds user credentials to the imported configurations.
- Uses the NordVPN DNS servers to prevent DNS request leaks.
- Disables IPv6 by default, to avoid IPv6 leaks.
- Sets the auto connect server of your choice for all NetworkManager connections, instead of per connection. (optional)

## 1. Requirements

### Debian/Ubuntu
```
sudo apt update && sudo apt install openvpn network-manager network-manager-gnome network-manager-openvpn-gnome
```

### Arch

```
sudo pacman -S networkmanager openvpn networkmanager-openvpn
```

## 2. Installation

```
sudo -H pip3 install nordnm
```

## 3. Usage Examples

*Get the latest configs, synchronise and then select a "normal" Netherlands server using tcp as auto-connect server:*

```
sudo nordnm --update --sync --auto-connect nl normal tcp
```

*View descriptions of other options:*

```
sudo nordnm --help
```
