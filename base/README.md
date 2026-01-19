# Podman Quadlet: Base

## Overview

The base cookbook provides foundational configuration for Fedora CoreOS systems. It includes:

- **fastfetch**: A system information tool displayed on login, with color-coded output (red for root, blue for regular users).
- **tmpfiles configuration**: Sets up required directories such as `/var/lib/virtiofs/data`.
- **QEMU guest agent**: Optional installation for better VM integration.
- **SSH key persistence**: Backs up and restores SSH host keys across reboots.

This cookbook is used as an implicit dependency for other cookbooks that run on Fedora CoreOS.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the base configuration.

```sh
sudo make clean install
```

You should see the **install-fastfetch.service** downloading and installing fastfetch.
On next login, fastfetch will display system information.

To verify the installation:

```sh
fastfetch --version
```

Finally, remove the configuration and its data.

```sh
sudo make uninstall clean
```
