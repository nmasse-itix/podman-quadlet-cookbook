# Podman Quadlets Cookbook

This project is a collection of Podman Quadlets for some widely used selfhosted software.
Your role is to write and maintain the Podman Quadlets.
You may be given Kustomize manifests, Helm charts, Docker Compose files, etc. that you HAVE TO convert in Podman Quadlets.

## Rules

- NEVER alter the files outside the "cookbooks" directory!
- You are ONLY ALLOWED to edit files in the sub-directories of the "cookbooks" directory.
- Before writing or editing a Podman Quadlet, you MUST read the `podman-systemd.unit(5)` man page!

## Architecture

- Convention over configuration: place the files at the right place and the tooling (Makefile) will take care of placing that file at the right location.
- Do not create Pods!

## Useful tools

- `podlet`: Podlet generates Podman Quadlet files from a Podman command, Docker command, Docker compose file, or existing Podman object (container, image, pod, volume, network, etc).

## Useful documentation

- @README.md: to get an overview of the project.
- @common.mk: to understand the development tooling.
- `podman-systemd.unit(5)`: syntax of the Podman Quadlet files.
- `podlet podman --help`: when you need to convert Docker commands.
- `podlet compose --help`: when you need to convert Docker Compose files.
- `podlet generate --help`: when you need to convert existing Podman objects.

