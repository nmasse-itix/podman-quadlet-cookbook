# Podman Quadlet Cookbook

[Podman Quadlets](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) are awesome, but vastly under-utilized in the Open Source communities.
This repository gathers all the recipes (hence the name "Cookbook") to deploy Open Source technologies using Podman Quadlets.

## Current cookbooks

- [nginx](nginx/): starts Nginx, content is initialized / updated from a GIT repository
- [postgresql](postgresql/): starts a PostgreSQL server, handles automated major upgrades, periodic backup and initialization of the database from the last backup.
- [nextcloud](nextcloud/): starts a Nextcloud server with all its dependencies, handles automated upgrades.

## License

MIT
