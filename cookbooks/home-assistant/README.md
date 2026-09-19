# Podman Quadlet: Home Assistant

## Overview

[Home Assistant](https://www.home-assistant.io/) is an open-source home automation
platform. This cookbook runs it as a Podman Quadlet.

This cookbook:

- Runs Home Assistant as a **non-root** container (host UID `10034`, GID `10000`).
- Uses **PostgreSQL** as the recorder (history) backend (requires the `postgresql` cookbook).
- Publishes the UI behind **Traefik** (requires the `traefik` cookbook).
- Stores `/config` (the whole Home Assistant state) as **precious data** on the virtiofs
  mount `/var/lib/virtiofs/data/home-assistant`, so it inherits the hypervisor's ZFS
  snapshot and backup levels.
- Bootstraps `/config` from operator-provided templates on first boot, then never touches
  it again.
- Runs a **weekly native backup** into `/config/backups`.
- Uses host networking, which Home Assistant needs for local device discovery (mDNS/SSDP).
- Supports automatic image updates via Podman auto-update (`AutoUpdate=registry`).

The upstream image `ghcr.io/home-assistant/home-assistant:stable` is multi-architecture
(amd64 + arm64), so it runs on the aarch64 target VM. Verified on version `2026.9.3`.

## Prerequisites

- The `postgresql` cookbook must be installed and running (recorder backend).
- The `traefik` cookbook must be installed and running (reverse proxy).
- The virtiofs mount `var-lib-virtiofs-data.mount` must be present (`/config` lives there).
- The operator must provide the configuration files listed below.

## Files the operator must provide

Everything site-specific is injected downstream into `/etc/quadlets/home-assistant/`.
The cookbook itself ships **no site value** — only examples (used for development and as
templates).

| Path                                              | Purpose                                                        |
| ------------------------------------------------- | ------------------------------------------------------------- |
| `/etc/quadlets/home-assistant/configuration.yaml` | Bootstrap Home Assistant configuration (copied to `/config`).  |
| `/etc/quadlets/home-assistant/secrets.yaml`       | Bootstrap secrets, incl. the recorder database URL + password. |

`home-assistant-init.service` only bootstraps `/config` when
`/etc/quadlets/home-assistant/configuration.yaml` is present; `home-assistant.service` only
starts once `/config/configuration.yaml` exists (created by the init unit on first boot, or
already present if Home Assistant was configured before). So on a fresh system nothing runs
until the operator provides the bootstrap files, and once Home Assistant owns `/config` the
files under `/etc/quadlets/home-assistant/` are no longer required.

Ready-to-use examples are provided under `config/examples/`. They are installed to
`/etc/quadlets/home-assistant/` during development and testing only, and are **not** part
of the production package. Adjust the following site-specific values in your own copies:

- the recorder database password in `secrets.yaml`;
- `http: trusted_proxies:` if Traefik connects from an address other than the loopback;
- the time zone (`homeassistant: time_zone:` in `configuration.yaml`) and the external URL,
  which are otherwise best set from the Home Assistant web interface;
- the MQTT broker address (radio head), configured from the web interface once the
  `mosquitto`/`zigbee2mqtt`/`zwave-js-ui` cookbooks are in place — out of scope here.

## Bootstrap configuration vs. live configuration — read this first

Home Assistant **owns `/config`**: it writes `configuration.yaml`, `secrets.yaml`,
`.storage/` and everything else from its own web interface. This conflicts with the usual
repository convention where `/etc/quadlets/` holds the live configuration. It is resolved
as follows:

- `/etc/quadlets/home-assistant/configuration.yaml` and `secrets.yaml` are **bootstrap
  templates**.
- `home-assistant-init.service` (a one-shot unit that runs before the container) copies each
  of them into `/config` **only if it is absent**. It never overwrites a file Home Assistant
  owns.
- The same unit creates the empty include targets `automations.yaml`, `scenes.yaml` and
  `scripts.yaml` (again, only if absent). `configuration.yaml` references them with `!include`
  so the UI can persist automations/scenes/scripts; without them Home Assistant would fail to
  parse the config on a fresh `/config` and fall back to recovery mode.
- **After first boot, `/config/configuration.yaml` is the live copy** — editing the file in
  `/etc/quadlets/home-assistant/` afterwards has **no effect**. To change the live
  configuration you must edit `/config/configuration.yaml` (on the virtiofs mount) or use the
  Home Assistant UI. This is the first thing most readers get wrong.

The shipped bootstrap configuration is enough for an unattended first start on an empty
`/config`, with the recorder already pointed at PostgreSQL.

## Reverse proxy

Behind a reverse proxy, Home Assistant rejects requests with `400 Bad Request` unless it is
told to trust the proxy. The bootstrap `configuration.yaml` therefore sets:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
```

`trusted_proxies` must list the address Traefik connects **from**. In this deployment Traefik
shares the host network and forwards to `127.0.0.1:8123`, so the loopback addresses are
correct. If your proxy connects from a different address, adjust the list — this is the single
most common deployment failure for Home Assistant.

The Traefik router shipped in `other/traefik/home-assistant.yaml` routes
`Host(\`home-assistant\`)` to `http://127.0.0.1:8123`.

## Recorder (PostgreSQL)

`other/postgresql/home-assistant.sql` creates the `home_assistant` role and database. The
recorder connection string is referenced from `configuration.yaml` via `!secret`, so the
password stays in `secrets.yaml` and never appears in a packaged file:

```yaml
recorder:
  db_url: !secret recorder_db_url
```

The upstream image ships `psycopg2` (2.9.12, verified on a running container), which is the
driver SQLAlchemy uses for `postgresql://` URLs. On first start the recorder creates its
schema (13 tables) in the `home_assistant` database.

## Native backup

Home Assistant's own backup format is the only one its interface can restore, and the one
that survives a major-version upgrade. The ZFS snapshots protect the bytes; this protects the
restore path.

The bootstrap `configuration.yaml` defines a **weekly** automation that calls the
`backup.create` service (Sundays at 04:30). Home Assistant writes the archive to
`/config/backups`, i.e. inside the virtiofs perimeter. Because this lives in the bootstrap
configuration, it only applies to instances started from the shipped template; on an existing
`/config` you set up the equivalent automation (or a scheduled backup) from the UI under
**Settings → System → Backups**.

## TCP ports

| Port | Protocol | Description                          |
| ---- | -------- | ------------------------------------ |
| 8123 | TCP      | Home Assistant web UI / API (HTTP).  |

Host networking is used, so Home Assistant also sends/receives the multicast traffic it needs
for mDNS/SSDP discovery.

## UID and GID

| Item | Value            |
| ---- | ---------------- |
| User | `10034` (`home-assistant`) |
| Group| `10000` (`itix-svc`)       |

## Deviations from the repository rules

- **Running as root — not needed.** The upstream image uses s6-overlay v3 with
  `ENTRYPOINT /init` and declares no `USER`, so it is designed to start as root. It was
  tempting to run it as root like `samba` and `vsftpd` do. That turned out to be
  unnecessary: s6-overlay v3 detects a non-root UID, fixes up `/run` itself, and then runs
  Home Assistant as that user. Verified on `2026.9.3` — with `User=10034`/`Group=10000` the
  process runs as host UID `10034` and owns everything it writes under `/config`, and the
  recorder connects to PostgreSQL normally. **This cookbook therefore does not run as root**,
  and needs no user-namespace/idmap workaround either.
- **Configuration is bootstrapped into `/config`, not kept read-only in `/etc/quadlets`.**
  Home Assistant owns its configuration directory (see "Bootstrap vs. live configuration"
  above), so the usual "configuration lives read-only in `/etc/quadlets`" rule cannot hold.
  The `/etc/quadlets/home-assistant/` files are one-time bootstrap templates, copied into
  `/config` only if absent.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Home Assistant (pulls in `postgresql` and `traefik`).

```sh
sudo make clean install
```

You should see the **home-assistant.service** waiting for PostgreSQL to be available, then
starting up. The first start takes one to three minutes.

Verify Home Assistant is running (no authentication needed on this endpoint):

```sh
curl -sSf http://127.0.0.1:8123/manifest.json
```

Open `http://127.0.0.1:8123/` to reach the onboarding page.

Restart the **home-assistant.target** unit.

```sh
sudo systemctl restart home-assistant.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make I_KNOW_WHAT_I_AM_DOING=yes uninstall clean
```
