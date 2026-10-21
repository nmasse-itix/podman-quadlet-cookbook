# Podman Quadlet: Lego

## Overview

Lego is a Let's Encrypt/ACME client started as a Podman Quadlet. It handles automatic SSL/TLS certificate issuance and renewal.

This cookbook:

- Runs Lego v5 with a configuration file (`/etc/quadlets/lego/lego.yaml`) describing the accounts, challenges and certificates.
- Obtains the missing certificates and renews the expiring ones via **lego.service**, started at boot and daily by **lego.timer**.
- Stores certificates with secure permissions (0600, owned by the `lego` user).
- Runs renewal hooks (`/etc/quadlets/lego/renew-hooks.d/*.sh`) to reload dependent services when certificates are obtained or renewed.

## Prerequisites

- Configuration file `/etc/quadlets/lego/lego.yaml` must exist. See [config/examples/lego.yaml](config/examples/lego.yaml) and the [Lego configuration file reference](https://go-acme.github.io/lego/references/ref-file/).
- DNS or HTTP challenge must be properly configured.

## Certificate naming convention

Lego v5 names the certificate files after the certificate ID in the configuration file: `/var/lib/quadlets/lego/certificates/<id>.{crt,key,issuer.crt,pem,json}`.

The other cookbooks (vsftpd, smtprelay, etc.) expect a certificate named **default**:

```yaml
certificates:
  default:
    domains:
      - ftp.example.tld
```

## How hooks work

1. Lego obtains or renews a certificate and calls its deploy hook (`/etc/quadlets/lego/deploy-hook.sh`, inside the container).
2. The deploy hook creates a `<id>.renewed` file next to the certificate.
3. **lego-hooks.path** notices the `.renewed` file and starts **lego-hooks.service**.
4. **lego-hooks.service** runs every script of `/etc/quadlets/lego/renew-hooks.d/` (on the host, as root) and removes the `.renewed` files.

Other cookbooks drop their hook in `other/lego/<cookbook>.sh`: it is installed in `/etc/quadlets/lego/renew-hooks.d/` automatically.

## Using a custom ACME server

To use an ACME server whose TLS certificate is signed by a private CA (Pebble, Step CA, etc.), set the `server` of the account in `lego.yaml` and add a drop-in to trust the CA:

```ini
# /etc/containers/systemd/lego.container.d/custom-ca.conf
[Container]
Environment=LEGO_CA_CERTIFICATES=/etc/lego/my-ca.pem
```

The CA certificate goes in `/etc/quadlets/lego/my-ca.pem` (`/etc/quadlets/lego` is mounted on `/etc/lego` in the container).

## Development mode

In development mode (`make fcos-vm` or `make install`, which install the examples), the **lego-dev.conf** drop-in replaces Lego with a script that generates a self-signed certificate for `localhost`, named `default`.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and fetch the initial certificate.

```sh
sudo make clean install
```

You should see the **lego.service** fetching a certificate from Let's Encrypt.
The certificate will be stored in `/var/lib/quadlets/lego/certificates/`.

Check the certificate:

```sh
sudo ls -la /var/lib/quadlets/lego/certificates/
```

The **lego.timer** will periodically check and renew the certificate before expiration.

To manually trigger a renewal check:

```sh
sudo systemctl start lego.service
```

Restart the **lego.target** unit.

```sh
sudo systemctl restart lego.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Upgrading from Lego v4

Lego v5 uses a configuration file and a new storage layout.
The simplest upgrade path is to obtain new certificates.

```sh
sudo systemctl stop lego.target lego-renew.timer
sudo rm -rf /var/lib/quadlets/lego/*
sudo rm -rf /etc/quadlets/lego/config.env /etc/quadlets/lego/renew-hook
sudo rm -rf /etc/containers/systemd/lego-run.container /etc/containers/systemd/lego-renew.container \
            /etc/containers/systemd/lego-run.container.d /etc/containers/systemd/lego-renew.container.d \
            /etc/systemd/system/lego-renew.timer /etc/systemd/system/lego-renew-hooks.service
sudo make install
```

Then, write `/etc/quadlets/lego/lego.yaml` (with a certificate named `default`) and start Lego.

```sh
sudo systemctl start lego.target
```

## Integration tests

```sh
sudo make pytest
```
