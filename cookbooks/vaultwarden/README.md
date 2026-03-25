# Podman Quadlet: Vaultwarden

## Overview

Vaultwarden is a Bitwarden-compatible password manager server started as a Podman Quadlet. It provides a self-hosted alternative to the official Bitwarden server, compatible with all Bitwarden clients.

This cookbook:

- Runs Vaultwarden as a rootless container with minimal privileges.
- Uses PostgreSQL as the database backend (requires the `postgresql` cookbook).
- Includes health checks to monitor the service status.
- Stores vault data in `/var/lib/virtiofs/data/vaultwarden/`.
- Supports automatic container image updates via Podman auto-update.

## Prerequisites

- The `postgresql` cookbook must be installed and running.
- Configuration file `/etc/quadlets/vaultwarden/config.env` must exist.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Vaultwarden.

```sh
sudo make clean install
```

You should see the **vaultwarden.service** waiting for PostgreSQL to be available, then starting up.

Verify Vaultwarden is running:

```sh
curl -sSf http://127.0.0.1:8080/
```

Access the web vault at `http://127.0.0.1:8080/` and configure your Bitwarden clients to use this server.

Restart the **vaultwarden.target** unit.

```sh
sudo systemctl restart vaultwarden.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
