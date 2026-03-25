# Podman Quadlet: QEMU User Static

## Overview

QEMU User Static provides multi-architecture container support using QEMU user-mode emulation. This allows running containers built for different CPU architectures (e.g., ARM containers on x86_64 hosts).

This cookbook:

- Builds a custom container image with QEMU static binaries.
- Registers QEMU interpreters with the kernel's binfmt_misc.
- Includes a timer to periodically rebuild the container image.
- Runs as a privileged one-shot service to register the interpreters.

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and register the QEMU interpreters.

```sh
sudo make clean install
```

You should see the **qemu-user-static-build.service** building the container image.
Then, the **qemu-user-static.service** registers the QEMU interpreters with the kernel.

Verify the registration:

```sh
ls /proc/sys/fs/binfmt_misc/
```

You should see entries for various architectures (e.g., `qemu-aarch64`, `qemu-arm`).

Test running a container for a different architecture:

```sh
podman run --rm docker.io/arm64v8/alpine uname -m
```

This should output `aarch64` even on an x86_64 host.

Restart the **qemu-user-static.target** unit.

```sh
sudo systemctl restart qemu-user-static.target
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```

## Integration tests

```sh
sudo make test
```
