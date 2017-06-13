# NordVPN-NetworkManager

This tool was put together quickly as an experimental way of handling .ovpn configs when it comes to NetworkManager. Currently it's specific to NordVPN, but maybe in the future it will be adapted into a general OpenVPN tool.

**Warning:**
*This tool is still highly experimental and is definitely not yet robust enough to use reliably. I take no responsibility for any unforseen problems it may cause.*

## Features:
- Downloads the latest NordVPN configuration files
- Provides a config for whitelisting or blacklisting certains countries by country code.
- Automatically adds user credentials to the imported configurations.
- Checks if servers are up before importing, by attempting to create a socket to the specified port.
- Removes active configurations if they have since gone down.
- Finds the best server to automatically connect to, using the average ping RTT (not super reliable, I know)
- Sets the auto connect server for all NetworkManager connections, instead of per connection. (optional)

## Requirements
- fping (for benchmarking)

## Usage
*Basic synchronise and select auto-connect server:*
```
sudo ./nordvpn-nm --sync --auto-connect nl
```

*View descriptions of other options:*
```
sudo ./nordvpn-nm --help
```
