# Podman Quadlet Cookbook

[Podman Quadlets](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) are awesome, but vastly under-utilized in the Open Source communities.
This repository gathers all the recipes (hence the name "Cookbook") to deploy Open Source technologies using Podman Quadlets.

## Current cookbooks

- [base](base/): base configuration for Fedora CoreOS with fastfetch, tmpfiles setup, and QEMU guest agent.
- [gitea](gitea/): self-hosted Git service, a lightweight GitHub/GitLab alternative.
- [keycloak](keycloak/): open source identity and access management server with PostgreSQL backend.
- [lego](lego/): Let's Encrypt/ACME client for automatic SSL/TLS certificate management and renewal.
- [miniflux](miniflux/): minimalist RSS/Atom feed reader with PostgreSQL backend.
- [nextcloud](nextcloud/): self-hosted file sync and share platform with all its dependencies, handles automated upgrades.
- [nginx](nginx/): Nginx web server with content initialized and updated from a GIT repository.
- [postgresql](postgresql/): PostgreSQL database server with automated major upgrades, periodic backup and restore capabilities.
- [qemu-user-static](qemu-user-static/): multi-architecture container support using QEMU user-mode emulation.
- [restic-server](restic-server/): REST server backend for restic backups with append-only mode and Prometheus metrics.
- [samba](samba/): SMB/CIFS file sharing server for network storage access.
- [seedbox](seedbox/): complete media server stack with Radarr, Sonarr, Lidarr, Prowlarr, qBittorrent, Jellyfin, and FlareSolverr.
- [traefik](traefik/): modern HTTP reverse proxy and load balancer with automatic service discovery.
- [vaultwarden](vaultwarden/): Bitwarden-compatible password manager server with PostgreSQL backend.
- [vmagent](vmagent/): Victoria Metrics agent for collecting and forwarding metrics.
- [vsftpd](vsftpd/): secure FTP server with TLS support and Let's Encrypt certificate integration.

## License

MIT
