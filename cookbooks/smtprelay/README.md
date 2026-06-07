# Podman Quadlet: smtprelay

## Overview

[smtprelay](https://github.com/decke/smtprelay) is a small Golang based SMTP relay/proxy server that accepts mail via SMTP and forwards it to an upstream smarthost (ex: Mailgun, Gmail, ...).

This cookbook:

- Builds a custom smtprelay container image locally, from CentOS Stream 10.
- Runs smtprelay directly as a dedicated, unprivileged UID/GID (no user namespace mapping).
- Listens on the submission port (587) with STARTTLS, authenticating clients against a local user/password file.
- Loads TLS certificates issued by the `lego` cookbook and reloads them automatically when renewed.
- Includes a timer to periodically rebuild the container image.

## Prerequisites

- Configuration file `/etc/quadlets/smtprelay/smtprelay.ini` must exist.
- File `/etc/quadlets/smtprelay/allowed_users.txt` must exist, listing the users allowed to relay mail.
- The `lego` cookbook should be configured to provide TLS certificates.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start smtprelay.

```sh
sudo make clean install
```

You should see the **smtprelay-build.service** building the smtprelay container image.
Then, the **smtprelay.service** should start up.

Verify smtprelay is running:

```sh
sudo systemctl status smtprelay.service
```

Send a test mail with [swaks](https://www.jetmore.org/john/code/swaks/):

```sh
swaks --to youremail@example.com --from youremail@example.com --auth-user yourusername --auth-password yourpassword --port 587 --tls
```

When Let's Encrypt certificates are renewed, the renewal hook automatically restarts smtprelay so it picks up the new certificates.

Restart the **smtprelay.target** unit.

```sh
sudo systemctl restart smtprelay.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
