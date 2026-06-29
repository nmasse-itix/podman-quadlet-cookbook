# Podman Quadlet Cookbook

[Podman Quadlets](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) are awesome, but vastly under-utilized in the Open Source communities.
This repository gathers all the recipes (hence the name "Cookbook") to deploy Open Source technologies using Podman Quadlets.

Each Cookbook is designed to run securely on an immutable [Fedora CoreOS](https://fedoraproject.org/coreos/) system: containers run as dedicated, non-root users with SELinux enforcing, and each Systemd unit performs a single, well-defined task. Cookbooks are composable building blocks — declare a dependency (e.g. `postgresql`, `traefik`) and it is installed and wired up automatically, configuration hooks included.

A common Makefile-based tooling (`make install`, `make package`, `make pytest`, ...) takes care of generating Quadlet/Systemd units, Butane/Ignition specs, and end-to-end tests, following a "convention over configuration" approach: drop your files in the right place and the tooling does the rest. See the [Developer's Guide](docs/DEVELOPERS_GUIDE.md) for details.

## Available Cookbooks

- [base](cookbooks/base/): base configuration for Fedora CoreOS with fastfetch, tmpfiles setup, and QEMU guest agent.
- [forgejo](cookbooks/forgejo/): self-hosted Git service (formerly Gitea), a lightweight GitHub/GitLab alternative, with PostgreSQL backend.
- [keycloak](cookbooks/keycloak/): open source identity and access management server with PostgreSQL backend.
- [lego](cookbooks/lego/): Let's Encrypt/ACME client for automatic SSL/TLS certificate management and renewal.
- [matrix](cookbooks/matrix/): self-hosted Matrix homeserver (Tuwunel) with Element Web client, automated backups and restore.
- [miniflux](cookbooks/miniflux/): minimalist RSS/Atom feed reader with PostgreSQL backend.
- [nextcloud](cookbooks/nextcloud/): self-hosted file sync and share platform with all its dependencies, handles automated upgrades.
- [nftables](cookbooks/nftables/): system-wide nftables firewall rules, composable via hooks from other cookbooks.
- [nginx](cookbooks/nginx/): Nginx web server with content initialized and updated from a GIT repository.
- [ntfy](cookbooks/ntfy/): simple HTTP-based pub-sub notification service with PostgreSQL backend.
- [postgresql](cookbooks/postgresql/): PostgreSQL database server with automated major upgrades, periodic backup and restore capabilities.
- [qemu-user-static](cookbooks/qemu-user-static/): multi-architecture container support using QEMU user-mode emulation.
- [quay](cookbooks/quay/): self-hosted container registry with Clair vulnerability scanning, image storage and proxy caching.
- [redis](cookbooks/redis/): in-memory data store used as a cache/queue backend by other cookbooks.
- [restic-server](cookbooks/restic-server/): REST server backend for restic backups with append-only mode and Prometheus metrics.
- [samba](cookbooks/samba/): SMB/CIFS file sharing server for network storage access.
- [seedbox](cookbooks/seedbox/): complete media server stack with Radarr, Sonarr, Lidarr, Prowlarr, qBittorrent, Jellyfin, and FlareSolverr.
- [smtprelay](cookbooks/smtprelay/): small SMTP relay/proxy that forwards mail to an upstream smarthost (Mailgun, Gmail, ...).
- [traefik](cookbooks/traefik/): modern HTTP reverse proxy and load balancer with automatic service discovery.
- [unifi](cookbooks/unifi/): Unifi Network Application with its MongoDB database backend.
- [vaultwarden](cookbooks/vaultwarden/): Bitwarden-compatible password manager server with PostgreSQL backend.
- [vmagent](cookbooks/vmagent/): Victoria Metrics agent for collecting and forwarding metrics.
- [vsftpd](cookbooks/vsftpd/): secure FTP server with TLS support and Let's Encrypt certificate integration.

## Documentation

- [Developer's Guide](docs/DEVELOPERS_GUIDE.md): architecture guidelines, development environment setup, and conventions to write your own Cookbook.
- [Testing Guide](docs/TESTING_GUIDE.md): how to write and run end-to-end tests for a Cookbook.

## License

MIT
