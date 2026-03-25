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
