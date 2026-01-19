# Podman Quadlet: Traefik

## Overview

Traefik is a modern HTTP reverse proxy and load balancer started as a Podman Quadlet. It provides automatic service discovery, SSL termination, and routing.

This cookbook:

- Runs Traefik as a rootless container with minimal privileges.
- Supports automatic HTTPS with Let's Encrypt integration.
- Includes health checks to monitor the service status.
- Stores configuration in `/etc/quadlets/traefik/` and state in `/var/lib/quadlets/traefik/`.
- Supports automatic container image updates via Podman auto-update.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Traefik.

```sh
sudo make clean install
```

You should see the **traefik.service** starting up.

Verify Traefik is running:

```sh
curl -sSf -H 'Host: ping' http://127.0.0.1/
```

Access the Traefik dashboard (if enabled in configuration):

```sh
curl http://127.0.0.1:8080/dashboard/
```

Restart the **traefik.target** unit.

```sh
sudo systemctl restart traefik.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
