# Podman Quadlet: Asterisk

## Overview

[Asterisk](https://www.asterisk.org/) is an open source PBX. This cookbook runs it as a SIP server for
phones on the local network, together with the TFTP server the phones fetch their configuration and
firmware from.

This cookbook:

- Builds a container image locally, from Alpine Linux 3.24, with the Asterisk 22 (LTS) and dnsmasq
  packages of the distribution.
- Runs Asterisk directly as a dedicated, unprivileged UID/GID (no user namespace mapping), with
  PJSIP as its only channel driver.
- Runs dnsmasq as a TFTP server only (no DNS, no DHCP), from the same image, as the same user.
- Loads an explicit list of Asterisk modules: what calls between SIP phones need, and nothing else.
- Includes a timer to rebuild the container image daily.

It does not provide voicemail, call recording, conferencing, a trunk to an operator, nor a web
interface.

## Prerequisites

- The `base` cookbook (implicit dependency), for the virtiofs mount.
- A virtiofs mount on `/var/lib/virtiofs/data`, which holds the TFTP root.
- 1 vCPU and 1 GB of RAM are enough for a household (not measured beyond that).
- Network access at the first boot, to pull `docker.io/library/alpine:3.24` and the Alpine packages.

## Files provided by the operator

| Path | Content |
|------|---------|
| `/etc/quadlets/asterisk/etc/pjsip.conf` | Transport, endpoints, authentication and AOR of each phone. Required. |
| `/etc/quadlets/asterisk/etc/extensions.conf` | Dialplan. Required. |
| `/etc/quadlets/asterisk/etc/indications.conf` | Call progress tones of the country. Optional: without it, Asterisk logs a warning and uses no tones of its own; the phones play theirs. |
| `/var/lib/virtiofs/data/asterisk/tftp/` | Configuration files and firmware images of the phones, as each vendor names them. Optional: the TFTP server also runs on an empty directory, so that files written later are served without a restart. |

Asterisk does not start without `pjsip.conf` and `extensions.conf`. Examples of both are in
`config/examples/etc/`.

The TFTP root is on the virtiofs mount rather than under `/etc/quadlets`, so that the host can write
it: a firmware image weighs tens of megabytes, which an Ignition file cannot carry. The files must be
readable by UID 10036.

The other files of `/etc/quadlets/asterisk/etc/` are part of the cookbook. Some are empty on purpose:
Asterisk reads them at startup whether or not the feature is used, and logs an error when they are
missing.

## Ports

| Port | Protocol | Service |
|------|----------|---------|
| 5060 | UDP | SIP |
| 10000-10999 | UDP | RTP (set in `rtp.conf`) |
| 69 | UDP | TFTP |

Both containers use host networking.

## UID and GID

| UID | GID | Usage |
|-----|-----|-------|
| 10036 | 10000 | Asterisk and dnsmasq |

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start Asterisk.

```sh
sudo make clean install
```

The **asterisk-build.service** builds the image, then **asterisk.service** starts. Check the
endpoints and the dialplan:

```sh
sudo podman exec asterisk asterisk -rx "pjsip show endpoints"
sudo podman exec asterisk asterisk -rx "dialplan show"
```

Make a phone ring without a second phone (`res_clioriginate`):

```sh
sudo podman exec asterisk asterisk -rx "channel originate PJSIP/101 application Wait 10"
```

Trace the SIP messages:

```sh
sudo podman exec asterisk asterisk -rx "pjsip set logger on"
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Known messages

At every start, `res_pjsip` logs twice: `There are no local system nameservers configured, resorting
to system resolution`. Measured on Alpine 3.24 with a populated `/etc/resolv.conf`. Name resolution
still works through the system resolver, and calls between phones addressed by IP do not use it.

## Container image updates

The daily rebuild pulls a newer `alpine:3.24` when there is one, and the containers restart on the
new image through `AutoUpdate=local`. A rebuild reuses the cached package layer as long as the base
image is unchanged: an Asterisk update published in the Alpine repository between two releases of
the base image is not picked up until the next one.
