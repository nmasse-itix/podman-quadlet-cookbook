# Podman Quadlet Cookbook

[Podman Quadlets](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) are awesome, but vastly under-utilized in the Open Source communities.
This repository gathers all the recipes (hence the name "Cookbook") to deploy Open Source technologies using Podman Quadlets.

## Architecture guidelines

- SELinux is enabled by default. Privileged containers are avoided whenever possible.
- Each cookbook runs as a dedicated Linux user, either directly with `--user=` or through user namespaces and UID/GID mapping.
- Persistent data are stored in `/var/lib/quadlets/$(PROJECT_NAME)`. Precious data are stored in `/var/lib/virtiofs/data/$(PROJECT_NAME)`.
- Configuration is stored in `/etc/quadlets/$(PROJECT_NAME)`.
- Each Systemd unit / Podman Quadlet perform only one task. Especially, the one-off initialization procedures, upgrade processes, etc. are run as separate units.
- Cookbooks are designed to be composable. If you need to deploy a software that needs PostgreSQL as database and a reverse proxy in front, just add the `postgresql` and `traefik` cookbooks as dependencies!

## Available Cookbooks

- [base](cookbooks/base/): base configuration for Fedora CoreOS with fastfetch, tmpfiles setup, and QEMU guest agent.
- [gitea](cookbooks/gitea/): self-hosted Git service, a lightweight GitHub/GitLab alternative.
- [keycloak](cookbooks/keycloak/): open source identity and access management server with PostgreSQL backend.
- [lego](cookbooks/lego/): Let's Encrypt/ACME client for automatic SSL/TLS certificate management and renewal.
- [miniflux](cookbooks/miniflux/): minimalist RSS/Atom feed reader with PostgreSQL backend.
- [nextcloud](cookbooks/nextcloud/): self-hosted file sync and share platform with all its dependencies, handles automated upgrades.
- [nginx](cookbooks/nginx/): Nginx web server with content initialized and updated from a GIT repository.
- [postgresql](cookbooks/postgresql/): PostgreSQL database server with automated major upgrades, periodic backup and restore capabilities.
- [qemu-user-static](cookbooks/qemu-user-static/): multi-architecture container support using QEMU user-mode emulation.
- [restic-server](cookbooks/restic-server/): REST server backend for restic backups with append-only mode and Prometheus metrics.
- [samba](cookbooks/samba/): SMB/CIFS file sharing server for network storage access.
- [seedbox](cookbooks/seedbox/): complete media server stack with Radarr, Sonarr, Lidarr, Prowlarr, qBittorrent, Jellyfin, and FlareSolverr.
- [traefik](cookbooks/traefik/): modern HTTP reverse proxy and load balancer with automatic service discovery.
- [vaultwarden](cookbooks/vaultwarden/): Bitwarden-compatible password manager server with PostgreSQL backend.
- [vmagent](cookbooks/vmagent/): Victoria Metrics agent for collecting and forwarding metrics.
- [vsftpd](cookbooks/vsftpd/): secure FTP server with TLS support and Let's Encrypt certificate integration.

## Cookbook layout

- `Makefile`: Cookbook's Makefile. Includes `../common.mk`. (**REQUIRED**)
- `overlay.bu`: Fedora CoreOS Butane Specifications to include in the generated Ignition files. (_OPTIONAL_)
- `fcos.bu`: The Fedora CoreOS Butane Specifications to build the dev & test FCOS Virtual Machine. (_OPTIONAL_)
- `config/*`: Cookbook's configuration files (read-only). Goes into `/etc/quadlets/$(PROJECT_NAME)`.
- `config/examples/*`: Cookbook configuration files (sample configuration, to be overwritten for each deployment). Goes into `/etc/quadlets/$(PROJECT_NAME)`.
- `config/examples/*.env`: Systemd environment files, potentially containing secrets (to be overwritten for each deployment). Goes into `/etc/quadlets/$(PROJECT_NAME)`.
- `sysctl.d/*.conf`: Sysctl settings. Goes into `/etc/sysctl.d`.
- `sysctl.d/examples/*.conf`: Sysctl settings (to be overwritten for each deployment). Goes into `/etc/sysctl.d`.
- `tmpfiles.d/*.conf`: systemd-tmpfiles.d settings. Goes into `/etc/tmpfiles.d`.
- `tmpfiles.d/examples/*.conf`: systemd-tmpfiles.d settings (to be overwritten for each deployment). Goes into `/etc/tmpfiles.d`.
- `profile.d/*.conf`: Bash profile settings. Goes into `/etc/profile.d`.
- `profile.d/examples/*.conf`: Bash profile settings (to be overwritten for each deployment). Goes into `/etc/profile.d`.
- `other/$(DEPENDENCY)/*`: Sample configuration files to inject into the Cookbook dependencies. For example, `other/postgresql/nextcloud.sql` goes into `/etc/quadlets/postgresql/init.d/nextcloud.sql`. This behavior is described in the `hooks.mk`.
- `hooks.mk`: the Makefile that registers rules to copy cookbook configuration files when used as a dependency.

## Pre-requisites

- Fedora / CentOS Stream / RHEL or derivative operating system.
- Systemd

## End-to-end testing

```
pip install -e .
pytest cookbooks/postgresql/tests/
```

## Development

To develop Podman Quadlets, it is advised to create a Fedora Virtual Machine dedicated to this task.

You can create a Fedora Virtual Machine with the following command:

```sh
sudo ./scripts/create-dev-vm.sh
```

Then, retrieve the IP address of your VM with the following command:

```sh
sudo virsh domifaddr quadlets
```

Then, on your host, add the following configuration to your `~/.ssh/config` file:

```
Host quadlets
        HostName <IP_ADDRESS_OF_YOUR_VM>
        User root
        ForwardAgent yes
        StrictHostKeyChecking=no
        UserKnownHostsFile=/dev/null
```

Finally, install the [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh&ssr=false#overview) extension for Visual Studio Code, and connect to your VM using the "Remote - SSH: Connect to Host..." command.

If needed, you can also connect to your VM using `ssh root@quadlets` from your terminal or from the libvirt console using `sudo virsh console quadlets` with the login `root` and the password `root`.

## License

MIT
