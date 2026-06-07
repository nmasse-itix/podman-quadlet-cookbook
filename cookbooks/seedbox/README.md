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
