# Podman Quadlet: Restic Server

## Overview

Restic REST Server is a backend server for the restic backup tool, started as a Podman Quadlet. It provides a REST API for storing and retrieving backup data.

This cookbook:

- Runs the restic REST server as a rootless container.
- Configures append-only mode for added security (backups can be added but not deleted).
- Enables Prometheus metrics for monitoring.
- Supports private repositories for multi-user setups.
- Stores backup data in `/var/lib/virtiofs/data/restic-server/`.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start the restic REST server.

```sh
sudo make clean install
```

You should see the **restic-server.service** starting up.

Verify the server is running:

```sh
curl -sSf http://127.0.0.1:8080/
```

Initialize a new repository (from a restic client):

```sh
restic -r rest:http://127.0.0.1:8080/myrepo init
```

The Prometheus metrics endpoint is available at:

```sh
curl http://127.0.0.1:8080/metrics
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
