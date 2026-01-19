# Podman Quadlet: Gitea

## Overview

Gitea is a lightweight, self-hosted Git service started as a Podman Quadlet. It provides a GitHub/GitLab-like experience for hosting Git repositories.

This cookbook:

- Runs Gitea as a rootless container with minimal privileges.
- Uses PostgreSQL as the database backend (requires the `postgresql` cookbook).
- Includes health checks to monitor the service status.
- Supports automatic container image updates via Podman auto-update.

## Prerequisites

- The `postgresql` cookbook must be installed and running.
- Configuration file `/etc/quadlets/gitea/config.env` must exist.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Gitea.

```sh
sudo make clean install
```

You should see the **gitea.service** waiting for PostgreSQL to be available, then starting up.

Verify Gitea is running:

```sh
curl -sSf http://127.0.0.1:3000/
```

Restart the **gitea.target** unit.

```sh
sudo systemctl restart gitea.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
