# Specification for smtprelay Quadlet Cookbook

You will have to develop a Quadlet cookbook for smtprelay, the mail transfer agent.

## Architecture

smtprelay is a mail transfer agent, deployed as a container image.
The container image will be built from the CentOS Stream 10 image (`quay.io/centos/centos:stream10`).

## Common requirements

- The `quay.io/centos/centos:stream10` docker image MUST have its own quadlet .image file.
- Each cookbook MUST have a dedicated unique UID. The GID is 10000.

## Security

Directly set the UID and GID in the quadlet file (no mapping).
Use the host network, like other quadlet cookbooks.
Let's Encrypt certificates will be handled by Traefik, so no need to worry about that in the smtprelay cookbook.

## Installation

Create the Containerfile for smtprelay, which will install the smtprelay binary.
The smtprelay binary can be obtained from the official releases on GitHub: https://github.com/decke/smtprelay.

Look at `cookbooks/base/config/install-fastfetch.sh` for an example of how to install a binary from a GitHub release in a Containerfile.

## Configuration

A sample configuration file for smtprelay:

```ini
; Hostname for this SMTP server
hostname = localhost

; File which contains username and password used for
; authentication before they can send mail.
allowed_users = /etc/smtprelay/allowed_users.txt

; Networks that are allowed to send mails to us
; Defaults to localhost. If set to "", then any address is allowed.
;allowed_nets = 0.0.0.0/0 ::/0
allowed_nets = 0.0.0.0/0

; Enable TLS for incoming connections on port 587
listen = starttls://0.0.0.0:587
local_cert = /etc/smtprelay/tls/localhost.crt
local_key  = /etc/smtprelay/tls/localhost.key

; Enforce encrypted connection on STARTTLS ports before
; accepting mails from client.
local_forcetls = true

; Relay Config (ex: Mailgun)
remotes = starttls://user:pass@smtp.mailgun.org:587
```

## Entrypoint

```sh
smtprelay --config /etc/smtprelay/smtprelay.ini -logfile=/dev/stdout
```

## How to test

```sh
swaks --to youremail@example.com --from youremail@example.com --auth-user yourusername --auth-password yourpassword --port 587 --tls
```

## Useful examples

You can copy the structure of the `miniflux` cookbook.
Look at the `samba` cookbook for an example of how to handle the container image building.
