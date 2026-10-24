# Podman Quadlet: CoreOS

## Overview

The coreos cookbook provides the configuration specific to Fedora CoreOS systems. It includes:

- **virtiofs data mount**: the **discover-virtiofs-tags.service** lists the virtiofs tags exposed by the hypervisor.
  When a `data` tag is present, **var-lib-virtiofs-data.mount** mounts it on `/var/lib/virtiofs/data` with the `container_file_t` SELinux context, so containers can use it.
- **tmpfiles configuration**: creates the `/var/lib/virtiofs` directory.
- **QEMU guest agent**: when running on KVM, **rpm-ostree-install-qemu-guest-agent.service** layers `qemu-guest-agent` with `rpm-ostree`, applies it live and starts it.
- **SSH key persistence** (Butane spec only): backs up the SSH host keys in `/var/lib/private/sshd` and restores them on reinstall, so the host keeps its identity.
- **DNS configuration** (Butane spec only): masks `systemd-resolved` and lets NetworkManager write `/etc/resolv.conf` directly (`rc-manager=file`).

This cookbook is an implicit dependency of every other cookbook, including [base](../base/).
It has no dependencies itself.

## Usage

This cookbook requires `rpm-ostree`, so it can only be installed on Fedora CoreOS.

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the CoreOS configuration.

```sh
sudo make clean install
```

On a KVM virtual machine, you should see the **rpm-ostree-install-qemu-guest-agent.service** installing the QEMU guest agent.

To verify the installation:

```sh
systemctl status qemu-guest-agent.service
findmnt /var/lib/virtiofs/data
```

Finally, remove the configuration and its data.

```sh
sudo make uninstall clean
```
