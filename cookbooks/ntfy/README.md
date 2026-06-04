# Podman Quadlet: ntfy

## Overview

ntfy is a simple HTTP-based pub-sub notification service started as a Podman Quadlet. It lets you send push notifications to your phone or desktop via scripts from any computer.

This cookbook:

- Runs ntfy as a rootless container with minimal privileges (UID 10027).
- Uses PostgreSQL as the database backend (requires the `postgresql` cookbook).
- Stores attachment cache on virtiofs (`/var/lib/virtiofs/data/ntfy`).
- Exposes ntfy through Traefik (requires the `traefik` cookbook).
- Includes health checks to monitor the service status.
- Supports automatic container image updates via Podman auto-update.

## Prerequisites

- The `postgresql` cookbook must be installed and running.
- The `traefik` cookbook must be installed and running.
- The `base` cookbook must be installed (provides the virtiofs mount).
- Configuration file `/etc/quadlets/ntfy/server.yml` must exist.

## Usage

Copy and customize the example configuration:

```sh
sudo cp config/examples/server.yml /etc/quadlets/ntfy/server.yml
sudo vi /etc/quadlets/ntfy/server.yml
```

In a separate terminal, follow the logs:

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start ntfy:

```sh
sudo make clean install
```

You should see the **ntfy.service** waiting for PostgreSQL to be available, then starting up.

Verify ntfy is running:

```sh
curl -sSf http://127.0.0.1:8080/v1/health
```

Restart the **ntfy.target** unit:

```sh
sudo systemctl restart ntfy.target
```

Finally, remove the quadlets, their configuration and their data:

```sh
sudo make uninstall clean
```
