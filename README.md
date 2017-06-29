# NordVPN-NetworkManager

This tool removes the need for manually handling OpenVPN configurations from NordVPN. It will synchronise the best servers from chosen countries into the NetworkManager VPN list. A synchronised VPN can then be chosen to auto-connect to, whenever NetworkManager brings an network connection up.

More documentation will be available when this repository is ready for public use.

**Warning:**
*This tool is still highly experimental and is definitely not yet robust enough to use reliably. I take no responsibility for any unforseen problems it may cause.*

## Features:
- Uses the latest NordVPN OpenVPN configuration files.
- Imports the 'best' server of each available type (country, category, protocol), based on latency and server load.
- Provides humanly readable connection names, so you can easily tell what each option offers.
- Provides settings for whitelisting or blacklisting certain countries from being synchronised.
- Automatically adds user credentials to the imported configurations.
- Uses the NordVPN DNS servers to prevent DNS request leaks.
- Disables IPv6 by default, to avoid IPv6 leaks.
- Sets the auto connect server of your choice for all NetworkManager connections, instead of per connection. (optional)

## Requirements
```
pip3 install -r requirements.txt
```

## Usage Examples
*get the latest configs, synchronise and then select auto-connect server:*
```
sudo python3 nordnm --update --sync --auto-connect nl normal tcp
```

*View descriptions of other options:*
```
sudo python3 nordnm --help
```
