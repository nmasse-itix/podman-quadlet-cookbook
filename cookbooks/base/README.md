# Podman Quadlet: Base

## Overview

The base cookbook provides the foundational configuration shared by all cookbooks, whatever the underlying operating system. It includes:

- **Tools installation**: the **install-tools.service** oneshot runs every script found in `/etc/quadlets/base/install-tools.d/`.
  Versions are pinned in `/etc/quadlets/base/install-tools.env`.
  The service is skipped when this file is absent.
- **fastfetch**: a system information tool installed by **install-tools.service** and displayed on login, with color-coded output (red for root, blue for regular users).
- **resolv.conf resync**: keeps `Network=host` containers in sync with the host's DNS.
  With `Network=host`, Podman snapshots `/etc/resolv.conf` at container creation and bind-mounts
  the copy, so a later DNS change (e.g. a DHCP renewal) never reaches running containers. A
  `systemd.path` unit watches `/etc/resolv.conf` and a oneshot service rewrites each host-network
  container's snapshot **in place** (same inode, no restart); bridged containers are left untouched.
  See [issue #1](https://github.com/nmasse-itix/podman-quadlet-cookbook/issues/1).
- **Container teardown drop-in** (example): a `container.d` drop-in that makes `systemctl stop` wait until the container has actually been removed.
- **Base images**: `fedora.image` and `centos-stream10.image` pull the base images used by other cookbooks to build their own images.
- **Users and groups**: creates the `itix-svc` service account (uid/gid 10000) and, in the Butane spec, the `itix` group (gid 1000) and removes the default `core` user.

This cookbook is an implicit dependency of every other cookbook, except [coreos](../coreos/).
It depends itself implicitly on the [coreos](../coreos/) cookbook, which holds everything specific to Fedora CoreOS.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the base configuration.

```sh
sudo make clean install
```

You should see the **install-tools.service** downloading and installing fastfetch.
On next login, fastfetch will display system information.

To verify the installation:

```sh
fastfetch --version
```

Finally, remove the configuration and its data.

```sh
sudo make uninstall clean
```
