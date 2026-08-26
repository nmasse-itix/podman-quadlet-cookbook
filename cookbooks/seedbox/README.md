# Podman Quadlet: Seedbox

## Overview

The Seedbox cookbook provides a complete media server stack started as Podman Quadlets. It includes all the tools needed for automated media acquisition and streaming.

This cookbook includes the following services:

- **qBittorrent**: BitTorrent client for downloading media.
- **Radarr**: Movie collection manager and downloader.
- **Sonarr**: TV series collection manager and downloader.
- **Lidarr**: Music collection manager and downloader.
- **Prowlarr**: Indexer manager for Radarr, Sonarr, and Lidarr.
- **Jellyfin**: Media server for streaming your collection.
- **FlareSolverr**: Proxy server to bypass Cloudflare protection for indexers.
- **cross-seed**: Automatically cross-seeds your torrents on other private trackers using your existing data.

All services:

- Run as rootless containers with minimal privileges.
- Share a common storage directory structure.
- Support automatic container image updates via Podman auto-update.

## Prerequisites

- Storage must be mounted at `/var/lib/virtiofs/data/`.
- Each service stores its configuration in `/var/lib/virtiofs/data/<service>/config/`.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start the seedbox stack.

```sh
sudo make clean install
```

You should see all services starting up. Access the web interfaces:

- **qBittorrent**: `http://127.0.0.1:8080/`
- **Radarr**: `http://127.0.0.1:7878/`
- **Sonarr**: `http://127.0.0.1:8989/`
- **Lidarr**: `http://127.0.0.1:8686/`
- **Prowlarr**: `http://127.0.0.1:9696/`
- **Jellyfin**: `http://127.0.0.1:8096/`
- **FlareSolverr**: `http://127.0.0.1:8191/`
- **cross-seed**: `http://127.0.0.1:2468/`

On its first start, **cross-seed** generates a template configuration file at
`/var/lib/virtiofs/ssd/cross-seed/config/config.js`. Edit it by hand to set at
least:

- `torznab`: your Prowlarr Torznab indexer URL(s) (with their API keys), e.g. `http://prowlarr:9696/1/api?apikey=<key>`.
- `torrentClients`: the qBittorrent connection string, e.g. `qbittorrent:http://<user>:<pass>@localhost:8080`.
- `linkDirs`: `["/data/storage/seed"]`, so that cross-seed hardlinks matches into the dedicated `seed` directory shared with qBittorrent.

Then restart **cross-seed.service** for the changes to take effect. See the
[cross-seed documentation](https://www.cross-seed.org/docs/basics/getting-started)
for the full set of options.

Restart the **seedbox.target** unit.

```sh
sudo systemctl restart seedbox.target
```

To restart individual services:

```sh
sudo systemctl restart jellyfin.service
sudo systemctl restart qbittorrent.service
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```

## Browser (LibreWolf over waypipe)

A browser is sometimes needed *on* the seedbox: to log into a private tracker,
to solve a challenge FlareSolverr cannot, or simply to reach an interface that
is only exposed on the seedbox's own network. Rather than a full remote-desktop
stack, this cookbook ships a browser that is displayed on your workstation with
[waypipe](https://gitlab.freedesktop.org/mstoeckl/waypipe): the browser runs
here, its Wayland protocol is forwarded over SSH, and it draws in a window on
your desktop like a local application.

### Where waypipe runs, and why it matters

`waypipe ssh` runs a waypipe *server* on the remote side. That server connects
back to your local waypipe client through an SSH-forwarded Unix socket, creates
a Wayland socket of its own, and starts the program under it -- so it has to
share a mount namespace with the browser.

waypipe therefore lives **in the container**, not on the Fedora CoreOS host:

- the host stays a stock, immutable CoreOS image with no layered package;
- the waypipe version is pinned by the image. This is not cosmetic: waypipe 0.9
  is the old C implementation and 0.10+ is the Rust rewrite, and they do not
  interoperate. The image is built on Fedora 44, so it carries the same waypipe
  as a Fedora 44 workstation, and the nightly rebuild keeps them in step.

The entry point on the host is a small shim,
`/etc/quadlets/seedbox/seedbox-waypipe.sh`, which you point waypipe at with
`--remote-bin`. It is a plain file rather than a shell function because
`ssh <host> <command>` runs a non-interactive, non-login shell, which never
sources `/etc/profile.d`.

### Usage

From your workstation (waypipe must be installed there too, at a matching
version):

```sh
waypipe --remote-bin /etc/quadlets/seedbox/seedbox-waypipe.sh \
        --remote-socket /run/seedbox/waypipe/wp \
        --no-gpu \
        ssh <user>@<seedbox> librewolf
```

`--remote-socket` is not optional in practice: by default waypipe picks a
randomised path under `/tmp`, and the shim has to know the directory in advance
to hand the socket to the container. `/run/seedbox/waypipe` is created by
`tmpfiles.d` and writable by the `wheel` group.

Logged in on the seedbox, `/etc/profile.d/seedbox.sh` provides
`seedbox-browser` (same arguments as the waypipe binary; with no argument it
opens a shell in the image), `seedbox-browser-rebuild` and
`seedbox-browser-command`.

### Why LibreWolf

The seedbox runs on aarch64, which rules out the two strongest options: neither
Tor Browser nor Mullvad Browser publishes a Linux arm64 build. LibreWolf does,
in a GPG-signed RPM repository, and it ships the hardening already applied:
`privacy.resistFingerprinting` on, uBlock Origin auto-installed through its
`policies.json`, telemetry and sponsored content gone, HTTPS-only mode on,
cookies partitioned, and app updates disabled -- which suits an image rebuilt
nightly by `librewolf-build.timer`.

`config/container/itix-hardening.cfg` is deliberately short. RFP works by making
every user look *identical*, so each pref flipped on top of it moves this
browser out of that crowd and makes it easier to single out. It only corrects
for what the container changes: letterboxing (the window is resized to arbitrary
dimensions by the waypipe client) and the download directory. The installed font
set is pinned in the `Containerfile` for the same reason -- a font list that
drifts every night is a fingerprint that drifts every night.

Note that arm64 Linux has no Widevine, so DRM streaming services will not work,
and `EncryptedMediaExtensions` is disabled by LibreWolf anyway.

### Configuration

`/etc/quadlets/seedbox/browser.conf` holds the image name, the uid/gid, the
profile and download directories, and escape hatches for extra podman or waypipe
arguments. Every setting uses the `${VAR:-default}` form, so an environment
variable still wins for one-off overrides. The file is owned by `root:root`
because the shim sources it with root privileges.

On this cookbook's defaults the profile lives in
`/var/lib/quadlets/seedbox/librewolf`; on a real seedbox, point
`BROWSER_PROFILE_DIR` at the SSD virtiofs mount and `BROWSER_DOWNLOAD_DIR` at
the import directory the \*arr stack already watches.

### Two security trade-offs worth knowing about

**The container runs with `--security-opt label=disable`.** SELinux checks
`connect()` on a Unix socket with the `connectto` permission against the
*listening process*, not against the socket file, so relabelling the socket does
not help:

```
avc: denied { connectto } comm="waypipe" path="/run/seedbox/waypipe/....sock"
     scontext=...:container_t:s0:c266,c919
     tcontext=...:unconfined_t:s0-s0:c0.c1023
     tclass=unix_stream_socket
```

The listener is the SSH session, which belongs to an unconfined user, and no
label this container could carry is allowed to connect to it. The alternative is
a system-wide policy module granting
`allow container_t unconfined_t:unix_stream_socket connectto`, which opens that
hole for *every* container on the host rather than for this one. Neither option
is free; this cookbook picks the narrower blast radius. The browser still runs
as an unprivileged uid, with no added capabilities, and the container is
discarded when the window closes.

**The browser is not on the host network.** Unlike the rest of this stack, it
gets podman's default network rather than `Network=host`, precisely so that a
hostile page cannot reach `127.0.0.1:8989` and friends -- the \*arr interfaces
are only protected by Traefik, and a browser is the one process here that
routinely executes untrusted code.

### Two sandboxes fighting over one capability

Worth knowing before you touch the podman flags or the `Containerfile`
entrypoint, because the failure modes look unrelated to each other:

- **Firefox's content sandbox chroots itself.** It does that inside a fresh user
  namespace, where it holds whatever is left in the *bounding* set, so
  `CAP_SYS_CHROOT` has to survive `--cap-drop=ALL`. Without it every content
  process logs `Sandbox: chroot: EPERM` and dies on SIGSEGV. It is the only
  capability needed -- `SYS_ADMIN` is not.
- **bubblewrap refuses to run when the caller holds capabilities without being
  setuid** (`bwrap: Unexpected capabilities but not setuid, old file caps
  config?`). On Fedora, gdk-pixbuf hands SVG decoding to glycin, which isolates
  its loaders with `bwrap --unshare-all`. When that fails, GTK cannot load an
  icon, falls back to `image-missing.svg`, fails again, and aborts the browser:
  `Gtk:ERROR:gtkiconhelper.c:495:ensure_surface_for_gicon: assertion failed`.

`--cap-add=SYS_CHROOT` satisfies the first and breaks the second, because podman
adds the capability to the *ambient* set as well when the container runs as a
non-root user. The image entrypoint therefore drops the ambient and inheritable
sets with `setpriv`, which needs no privilege and leaves the bounding set alone.
Each sandbox then sees what it expects.
