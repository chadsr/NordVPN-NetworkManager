# NordVPN-NetworkManager

This tool removes the need for manually handling OpenVPN configurations from NordVPN. It will synchronise the best servers from selected countries into the NetworkManager VPN list. An active connection can then be chosen to auto-connect to, whenever NetworkManager brings an network connection up.

More documentation will be available when this repository is ready for public use.

**Warning:**
*This tool is still highly experimental and is definitely not yet robust enough to use reliably. I take no responsibility for any unforseen problems it may cause.*

## Features:
- Downloads the latest NordVPN configuration files
- Provides a config for whitelisting or blacklisting certains countries by country code.
- Automatically adds user credentials to the imported configurations.
- Imports the best server of each category (based on latency and server load) from each of the selected countries in $HOME/.nordnm/settings.conf
- Sets the auto connect server of your choice for all NetworkManager connections, instead of per connection. (optional)

## Requirements
- fping (for benchmarking)

## Usage
*Basic synchronise and select auto-connect server:*
```
sudo python3 nordnm --sync --auto-connect nl normal tcp
```

*View descriptions of other options:*
```
sudo python3 nordnm --help
```
