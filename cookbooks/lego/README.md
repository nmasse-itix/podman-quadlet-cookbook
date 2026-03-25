# Podman Quadlet: Lego

## Overview

Lego is a Let's Encrypt/ACME client started as a Podman Quadlet. It handles automatic SSL/TLS certificate issuance and renewal.

This cookbook:

- Runs an initial certificate fetch via **lego-run.service** when no certificates exist.
- Schedules automatic certificate renewal via **lego-renew.timer**.
- Stores certificates with secure permissions (umask 0077).
- Supports renewal hooks to reload dependent services when certificates are renewed.

## Prerequisites

- Configuration file `/etc/quadlets/lego/config.env` must exist with ACME configuration.
- DNS or HTTP challenge must be properly configured.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and fetch the initial certificate.

```sh
sudo make clean install
```

You should see the **lego-run.service** fetching a certificate from Let's Encrypt.
The certificate will be stored in `/var/lib/quadlets/lego/certificates/`.

Check the certificate:

```sh
sudo ls -la /var/lib/quadlets/lego/certificates/
```

The **lego-renew.timer** will periodically check and renew the certificate before expiration.

To manually trigger a renewal check:

```sh
sudo systemctl start lego-renew.service
```

Restart the **lego.target** unit.

```sh
sudo systemctl restart lego.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
