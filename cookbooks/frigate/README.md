# Podman Quadlet: Frigate

## Overview

[Frigate](https://frigate.video/) is a network video recorder with object detection for IP cameras.
This cookbook runs it as a Podman Quadlet.

This cookbook:

- Runs the upstream image `ghcr.io/blakeblackshear/frigate`, pinned to a full version (`0.18.2`).
  The manifest is multi-architecture (amd64 + arm64).
- Runs Frigate as root inside its container, as the image requires (s6-overlay).
- Stores the configuration, the database and the recordings as **precious data** on the virtiofs
  mount `/var/lib/virtiofs/data/frigate`, so that they inherit the hypervisor's ZFS snapshots,
  quota and backups.
- Seeds the configuration file on first boot, then never touches it again: Frigate owns it, and its
  web interface writes the cameras, the masks and the zones back to it.
- Binds the unauthenticated listeners of Frigate and go2rtc to the loopback.
- Detects objects with OpenVINO on the CPU, the default of a new Frigate 0.18 configuration.
- Uses host networking.

It does not provide MQTT, a reverse proxy, nor any camera definition.

## Prerequisites

- The `base` cookbook (implicit dependency), for the virtiofs mount.
- A virtiofs mount on `/var/lib/virtiofs/data`, sized for the recordings.
- Network access at the first boot, to pull the image (about 2 GB on arm64).
- CPU and memory in proportion to the cameras. Frigate's own figures are for hardware detectors;
  on a CPU, measure the inference time it reports under *System metrics*.

## Files

| Path | Content |
|------|---------|
| `/etc/quadlets/frigate/config.yml` | Seed of the configuration file. Shipped by the cookbook; an operator may replace it before the first boot. |
| `/etc/quadlets/frigate/init.sh` | Copies the seed when Frigate has no configuration file yet. |
| `/var/lib/virtiofs/data/frigate/config/` | Mounted on `/config`: `config.yml`, the SQLite database, the model cache, the backup of the configuration made before each migration. |
| `/var/lib/virtiofs/data/frigate/media/` | Mounted on `/media/frigate`: recordings, clips, snapshots, exports. |

`frigate.service` only starts once `/var/lib/virtiofs/data/frigate/config/config.yml` exists. On a
fresh system, `frigate-init.service` creates it from the seed. Once it exists, the seed is never
read again: changing `/etc/quadlets/frigate/config.yml` has no effect on a running installation.

## The seed

The seed is the default configuration of Frigate 0.18, plus three restrictions:

- `networking.listen.internal: 127.0.0.1:5000`. Port 5000 serves the UI and the API without
  authentication. The health check and nginx reach it over the loopback; nothing else needs it.
- `go2rtc.api.listen: 127.0.0.1:1984`. The go2rtc API is not authenticated, and it accepts new
  stream sources, `exec:` included. It listens on every address by default.
- `go2rtc.rtsp.listen: 127.0.0.1:8554`. The RTSP restream is not authenticated either.

MQTT is disabled. `cameras` is empty: cameras are added from the web interface, or by editing
`config.yml` on the data mount.

## Ports

| Port | Bound to | Use |
|------|----------|-----|
| `8971/tcp` | all | Web interface and API, authenticated, over TLS with a self-signed certificate |
| `8555/tcp+udp` | all | WebRTC, for live views in a browser |
| `5000/tcp` | loopback | Web interface and API, **unauthenticated** |
| `1984/tcp` | loopback | go2rtc API, **unauthenticated** |
| `8554/tcp` | loopback | RTSP restream, unauthenticated |

## First login

Frigate creates an `admin` user at its first start and prints its password in the journal:

```sh
journalctl -u frigate.service | grep -A1 -i password
```

Change it under *Settings > Users*. To print a new one, set `auth.reset_admin_password: true` in
`config.yml` and restart Frigate.

## Upgrades

The tag is pinned in `frigate.image` and `frigate.container`, and both must change together. A new
minor version migrates `config.yml` in place at its first start, after copying it to
`backup_config.yaml`. There is no migration back: going back to an older version means restoring
the data mount from a snapshot taken before the upgrade.

## Usage

```sh
sudo systemctl start frigate.target
sudo systemctl status frigate.service
sudo podman logs -f frigate
curl -k https://localhost:8971/
```

## Shared memory

A camera detecting at 720p takes about 35 MB of shared memory: 1280 × 720 × 1.5 bytes for each of
the 25 frames Frigate keeps. Logs and nginx cache take up to 50 MB more. `ShmSize=512m` thus covers
eight such cameras and two added while Frigate runs. A shared memory too small shows as `Bus error`
in the journal. The calculator in the upstream installation guide gives the size for other setups.
