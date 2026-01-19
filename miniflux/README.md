# Podman Quadlet: Miniflux

## Overview

Miniflux is a minimalist RSS/Atom feed reader started as a Podman Quadlet. It is fast, lightweight, and focuses on simplicity.

This cookbook:

- Runs Miniflux as a rootless container with minimal privileges.
- Uses PostgreSQL as the database backend (requires the `postgresql` cookbook).
- Includes health checks to monitor the service status.
- Supports automatic container image updates via Podman auto-update.

## Prerequisites

- The `postgresql` cookbook must be installed and running.
- Configuration file `/etc/quadlets/miniflux/miniflux.conf` must exist.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Miniflux.

```sh
sudo make clean install
```

You should see the **miniflux.service** waiting for PostgreSQL to be available, then starting up.

Verify Miniflux is running by accessing the web interface or using the health check:

```sh
curl -sSf http://127.0.0.1:8080/healthcheck
```

Restart the **miniflux.target** unit.

```sh
sudo systemctl restart miniflux.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
