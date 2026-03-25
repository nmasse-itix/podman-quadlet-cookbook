# Podman Quadlet: Samba

## Overview

Samba is an SMB/CIFS file sharing server started as a Podman Quadlet. It allows sharing files and directories over the network with Windows, macOS, and Linux clients.

This cookbook:

- Builds a custom Samba container image locally.
- Runs Samba with configurable shares via drop-in configuration files.
- Supports user authentication with system users mapped into the container.
- Includes a timer to periodically rebuild the container image.
- Only starts if at least one share configuration file exists.

## Prerequisites

- Share configuration files must exist in `/etc/quadlets/samba/smb.conf.d/` with names ending in `shares.conf`.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Samba.

```sh
sudo make clean install
```

You should see the **samba-build.service** building the Samba container image.
Then, the **samba.service** should start up.

Verify Samba is running:

```sh
sudo systemctl status samba.service
```

Test connectivity from a client:

```sh
smbclient -L //localhost -N
```

Connect to a share:

```sh
smbclient //localhost/sharename -U username
```

Restart the **samba.target** unit.

```sh
sudo systemctl restart samba.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
