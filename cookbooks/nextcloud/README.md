# Podman Quadlet: Nextcloud

## Overview

Nextcloud is a self-hosted file sync and share platform started as a Podman Quadlet. It provides cloud storage, collaboration, and productivity features.

This cookbook runs a complete Nextcloud stack:

- **nextcloud-app**: The main Nextcloud PHP application.
- **nextcloud-nginx**: Nginx web server to serve Nextcloud.
- **nextcloud-redis**: Redis for caching and session management.
- **nextcloud-init**: Initializes the Nextcloud installation.
- **nextcloud-upgrade**: Handles Nextcloud version upgrades.
- **nextcloud-cron**: Scheduled background jobs via timer.
- **nextcloud-collabora**: Optional Collabora Online for document editing.

This cookbook uses PostgreSQL as the database backend (requires the `postgresql` cookbook).

## Prerequisites

- The `postgresql` cookbook must be installed and running.
- Configuration file `/etc/quadlets/nextcloud/config.env` must exist.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Nextcloud.

```sh
sudo make clean install
```

You should see the services starting in order:

1. **nextcloud-redis.service** starts the Redis cache.
2. **nextcloud-init.service** initializes Nextcloud if needed.
3. **nextcloud-app.service** starts the PHP application.
4. **nextcloud-nginx.service** starts the web server.
5. **nextcloud-upgrade.service** runs any pending upgrades.
6. **nextcloud-cron.timer** schedules background jobs.

Access Nextcloud at `http://127.0.0.1/`.

Restart the **nextcloud.target** unit.

```sh
sudo systemctl restart nextcloud.target
```

To manually run background jobs:

```sh
sudo systemctl start nextcloud-cron.service
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
