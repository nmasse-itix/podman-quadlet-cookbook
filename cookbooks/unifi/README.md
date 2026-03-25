# Podman Quadlet: Unifi Network Application

## Overview

The Unifi software is a powerful, enterprise wireless software engine ideal for high-density client deployments requiring low latency and high uptime performance.

This cookbook:

- Runs the Unifi Network Application as a rootless container with minimal privileges.
- Uses the supplied MongoDB as the database backend.
- Includes health checks to monitor the service status.
- Stores backup in `/var/lib/virtiofs/data/unifi/`.
- Supports automatic container image updates via Podman auto-update.

## Prerequisites

- Configuration file `/etc/quadlets/unifi/config.env` must exist.

## Container images

- lscr.io/linuxserver/unifi-network-application:latest
- docker.io/library/mongo:8

