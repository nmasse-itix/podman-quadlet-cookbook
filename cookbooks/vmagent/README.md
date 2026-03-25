# Podman Quadlet: vmagent

## Overview

vmagent is a Victoria Metrics agent started as a Podman Quadlet. It collects metrics from various sources and forwards them to a Victoria Metrics or Prometheus-compatible remote storage.

This cookbook:

- Runs vmagent as a rootless container with minimal privileges.
- Uses environment-based configuration via global and local environment files.
- Stores scraped data temporarily in `/var/lib/quadlets/vmagent/` for reliability.
- Reads scrape configuration from `/etc/quadlets/vmagent/conf.d/`.
- Supports automatic container image updates via Podman auto-update.

## Prerequisites

- Configuration file `/etc/quadlets/vmagent/vmagent.local.env` must exist.
- Global configuration in `/etc/quadlets/vmagent/vmagent.global.env`.
- Scrape targets configured in `/etc/quadlets/vmagent/conf.d/`.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start vmagent.

```sh
sudo make clean install
```

You should see the **vmagent.service** starting up and beginning to scrape configured targets.

Verify vmagent is running:

```sh
sudo systemctl status vmagent.service
```

Check vmagent's own metrics:

```sh
curl http://127.0.0.1:8429/metrics
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
