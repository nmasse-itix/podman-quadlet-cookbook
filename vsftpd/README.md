# Podman Quadlet: vsftpd

## Overview

vsftpd (Very Secure FTP Daemon) is started as a Podman Quadlet. It provides a secure FTP server with TLS support.

This cookbook:

- Builds a custom vsftpd container image locally.
- Supports TLS encryption with automatic certificate loading from Let's Encrypt (integrates with the `lego` cookbook).
- Maps system users into the container for authentication.
- Includes a timer to periodically rebuild the container image.
- Reloads certificates automatically when renewed.

## Prerequisites

- Configuration file `/etc/quadlets/vsftpd/vsftpd.conf.d/local.conf` must exist.
- For TLS support, the `lego` cookbook should be configured to provide certificates.

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

When Let's Encrypt certificates are renewed, the **vsftpd-load-renewed-certificate.service** automatically reloads them.

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
sudo make test
```
