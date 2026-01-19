# Podman Quadlet: Keycloak

## Overview

Keycloak is an open source identity and access management server started as a Podman Quadlet. It provides single sign-on (SSO), identity brokering, and user federation capabilities.

This cookbook:

- Builds a custom Keycloak container image locally for optimized startup.
- Runs Keycloak with PostgreSQL as the database backend (requires the `postgresql` cookbook).
- Includes a timer to periodically rebuild the container image.
- Includes health checks to monitor the service status.

## Prerequisites

- The `postgresql` cookbook must be installed and running.
- Configuration file `/etc/quadlets/keycloak/config.env` must exist.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Keycloak.

```sh
sudo make clean install
```

You should see the **keycloak-build.service** building the optimized Keycloak container image.
Then, the **keycloak.service** should start up after waiting for PostgreSQL to be available.

Verify Keycloak is running:

```sh
curl -sSf http://127.0.0.1:8080/health
```

Restart the **keycloak.target** unit.

```sh
sudo systemctl restart keycloak.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
