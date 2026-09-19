# Podman Quadlet: Mosquitto

## Overview

[Eclipse Mosquitto](https://mosquitto.org/) is a lightweight MQTT broker. This cookbook
runs it as a Podman Quadlet to serve as the MQTT backbone of a home-automation stack
(Home Assistant, `zigbee2mqtt`, ESPHome, ...).

This cookbook:

- Runs Mosquitto as a rootless container (UID 10033) with minimal privileges.
- Binds a plain-MQTT listener on **loopback only** (`127.0.0.1:1883`). Nothing listens on
  the LAN by default.
- Terminates TLS **at Traefik** (port 443, demultiplexed by SNI), not inside the broker —
  it depends on the `traefik` cookbook.
- Refuses anonymous access; authentication and topic authorization come from operator-provided
  files.
- Stores retained messages and client sessions on the virtiofs precious-data mount
  (`/var/lib/virtiofs/data/mosquitto/`), so the host's ZFS snapshots and backups pick them up.
- Logs everything to stdout, so `journalctl` is the single place to look.
- Supports automatic container image updates via Podman auto-update.

The image is `docker.io/library/eclipse-mosquitto:2`, a multi-architecture manifest
(amd64 + arm64, verified 2026-09-19, version 2.1.2), as required by the aarch64 target.

## Prerequisites

- The `traefik` cookbook must be installed and running (installed automatically as a
  dependency).
- The virtiofs data mount `/var/lib/virtiofs/data` must be present (provided by the
  `fcos-with-virtiofs` template / the `base` cookbook).
- The operator must provide a password file and an ACL file (see below). Until the
  password file exists, the broker is intentionally **not** started (the units carry a
  `ConditionPathExists=/etc/quadlets/mosquitto/passwd` guard).

## Files the operator must provide

Both files are provided by the operator (e.g. an Ansible role from a vault) and are **not**
part of the package. Working examples ship under `config/examples/` for development only.

| Path                                | Mode | Owner        | Purpose                                   |
|-------------------------------------|------|--------------|-------------------------------------------|
| `/etc/quadlets/mosquitto/passwd`    | 0640 | `10033:10000`| MQTT username/password database           |
| `/etc/quadlets/mosquitto/acl`       | 0640 | `10033:10000`| Per-user topic authorization              |

Site-specific Traefik routing (real SNI host name + certificate resolver) is injected
downstream as an overlay into `/etc/quadlets/traefik/conf.d/` — see
[TLS at Traefik](#tls-at-traefik) below. No site value is baked into this cookbook.

### Generating a password entry

Use `mosquitto_passwd` (available inside the broker image, or from the `mosquitto-clients`
package):

```sh
# Create/replace the file and add the first user:
mosquitto_passwd -c -b /etc/quadlets/mosquitto/passwd homeassistant 'S3cr3t!'
# Add more users (omit -c so the file is not truncated):
mosquitto_passwd -b /etc/quadlets/mosquitto/passwd zigbee2mqtt 'An0th3r!'
```

Then make sure ownership and mode are correct:

```sh
chown 10033:10000 /etc/quadlets/mosquitto/passwd
chmod 0640 /etc/quadlets/mosquitto/passwd
```

The ACL file uses Mosquitto's ACL syntax; see `config/examples/acl` for a starting point.
Because `acl_file` is set and anonymous access is refused, access is **default-deny**: an
authenticated user can only touch the topics granted to it.

## TLS at Traefik

The broker speaks **plain MQTT** on loopback. Traefik terminates TLS on port 443 and
demultiplexes connections by SNI, forwarding the plaintext stream to `127.0.0.1:1883`. This
is expressed as a Traefik **TCP** router (not an HTTP one), shipped as a hook fragment in
`other/traefik/mosquitto.yaml` and installed to `/etc/quadlets/traefik/conf.d/mosquitto.yaml`
during development.

What this implies for clients:

- All clients are **remote** and connect over **TLS on port 443** using the broker's SNI host
  name (e.g. `mqtt.itix.fr` in production, `mqtt` in the shipped example), *not* to port 1883.
  Example round trip through Traefik:

  ```sh
  mosquitto_sub --cafile /path/to/ca.crt -h mqtt -p 443 -u homeassistant -P '…' -t 'test/#' &
  mosquitto_pub --cafile /path/to/ca.crt -h mqtt -p 443 -u homeassistant -P '…' -t 'test/x' -m hello
  ```

- **Credentials travel in clear text between Traefik and the broker** over the loopback
  interface (Traefik has already terminated TLS). This is acceptable because loopback traffic
  never leaves the host, but it is stated here so it is not a surprise.

- The shipped fragment uses a bare `tls: {}`, which makes Traefik serve its own self-signed
  certificate — good enough to test the path end-to-end. In production the operator overlays a
  fragment with the real SNI host name and `certResolver: le` (the certificate resolver is a
  site value and is kept commented out in the package).

A TCP router whose `HostSNI` is not `` `*` `` **requires** a `tls` section, a TCP service uses
`address:` (never `url:`), and this router coexists on the `https` entry point with the HTTP
routers of the other cookbooks, which match `HostSNI(`*`)` implicitly.

### Making the broker listen on the LAN (optional)

If an operator nevertheless wants the broker to accept connections directly on the LAN, they
can drop a fragment such as `listener 8883 0.0.0.0` (plus its own TLS/authentication settings)
into `/etc/quadlets/mosquitto/conf.d/`. This cookbook ships no LAN listener and no firewall
rules.

## Ports

| Port | Bind        | Purpose                                             |
|------|-------------|-----------------------------------------------------|
| 1883 | `127.0.0.1` | Plain MQTT listener (loopback only)                 |
| 443  | Traefik     | TLS-terminated MQTT ingress (SNI-routed by Traefik) |

Port 1883 is above 1024, so the non-root container binds it without any capability.

## UID and GID

- User: `mosquitto`, UID **10033**
- Group: `itix-svc`, GID **10000**

## Health check

The health probe is a bare TCP connect to the listener (`nc -z 127.0.0.1 1883`). It is
preferred over a credentialed `mosquitto_sub` on `$SYS/#` because it needs **no secret** —
the operator's password file may legitimately not be in place yet, and the probe must not
depend on it. As a side effect, each probe produces a benign `New connection` /
`disconnected: connection closed by client` log pair in the journal; raise `HealthInterval`
or set `connection_messages false` in a `conf.d` fragment if that noise is unwanted.

## Deviations from the repository conventions

- **No TLS inside the container and no `lego` dependency.** TLS is Traefik's job, mirroring
  the production montage (Traefik `HostSNI` + `certResolver: le` in front of port 1883). The
  Traefik hook is a **TCP** router rather than the usual HTTP one.
- **The whole `/etc/quadlets/mosquitto` directory is mounted read-only** into the container
  (at the same path) rather than mounting individual files, so that `mosquitto.conf`, the
  `conf.d/` fragments and the operator-provided `passwd`/`acl` all appear without enumerating
  them, and host and container paths stay identical.
- **Health check is an unauthenticated TCP connect** (see above), not the credentialed
  `$SYS/#` subscription some deployments use.
- **The `conf.d/` directory is packaged as an empty directory** because Mosquitto's
  `include_dir` fails if the directory is missing (verified against 2.1.2; it is also
  non-recursive and only reads `*.conf`).

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Mosquitto (pulls in `traefik`).

```sh
sudo make clean install
```

Verify the broker is listening on loopback (and nowhere else):

```sh
ss -ltnp | grep 1883
```

Publish/subscribe round trip with a password (using the shipped development credentials):

```sh
mosquitto_sub -h 127.0.0.1 -p 1883 -u homeassistant -P homeassistant -t 'test/#' &
mosquitto_pub -h 127.0.0.1 -p 1883 -u homeassistant -P homeassistant -t 'test/x' -m hello
```

Anonymous access must be refused:

```sh
mosquitto_pub -h 127.0.0.1 -p 1883 -t 'test/x' -m nope   # -> Connection Refused: not authorised.
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make I_KNOW_WHAT_I_AM_DOING=yes uninstall clean
```
