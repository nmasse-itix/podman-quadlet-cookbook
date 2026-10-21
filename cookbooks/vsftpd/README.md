# Podman Quadlet: vsftpd

## Overview

vsftpd (Very Secure FTP Daemon) is started as a Podman Quadlet. It provides a secure FTP server with TLS support.

This cookbook:

- Builds a custom vsftpd container image locally.
- Supports TLS encryption with a certificate provided by the `lego` cookbook (Let's Encrypt in production, self-signed in development).
- Maps system users into the container for authentication.
- Includes a timer to periodically rebuild the container image.
- Reloads certificates automatically when renewed.

## Prerequisites

- Configuration file `/etc/quadlets/vsftpd/vsftpd.conf.d/local.conf` must exist.
- For TLS support, the `lego` cookbook must be configured to provide a certificate named `default` (see the lego cookbook's README).
- The volumes to share must be mounted on `/data` with a drop-in (see [dropins/vsftpd.container.d/storage.conf](dropins/vsftpd.container.d/storage.conf)).

## TLS certificates

The TLS settings are in `local.conf` (see [config/examples/vsftpd.conf.d/local.conf](config/examples/vsftpd.conf.d/local.conf)):

```ini
ssl_enable=YES
rsa_cert_file=/etc/vsftpd/tls/default.crt
rsa_private_key_file=/etc/vsftpd/tls/default.key
```

- Before starting vsftpd, **vsftpd.service** copies the certificates from `/var/lib/quadlets/lego/certificates` to `/run/quadlets/vsftpd/tls` (mounted on `/etc/vsftpd/tls` in the container).
- When lego obtains or renews a certificate, its renewal hook ([other/lego/vsftpd.sh](other/lego/vsftpd.sh)) restarts **vsftpd.service** (if it is running) to load the new certificate.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start vsftpd.

```sh
sudo make clean install
```

You should see the **vsftpd-build.service** building the vsftpd container image.
Then, the **vsftpd.service** should start up.

Verify vsftpd is running:

```sh
sudo systemctl status vsftpd.service
```

Test FTP connectivity:

```sh
ftp localhost
```

Or with TLS:

```sh
lftp -u username localhost
```

When the certificates are renewed by lego, **vsftpd.service** is restarted automatically to load them.

Restart the **vsftpd.target** unit.

```sh
sudo systemctl restart vsftpd.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make pytest
```
