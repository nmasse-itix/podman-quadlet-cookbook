# Podman Quadlet: vLLM

## Overview

This cookbook serves large language models with [vLLM](https://docs.vllm.ai/) on a
single NVIDIA GPU, and multiplexes several models on that GPU using
[llmsnap](https://github.com/napmany/llmsnap).

Rather than a cold restart on every model switch (~128 s), llmsnap uses vLLM's
**sleep mode**: the outgoing model is put to sleep (its weights moved from VRAM to
host RAM) and woken up on demand (~11 s). Only one model is awake at a time, which
lets two large models share a 24 GB GPU (e.g. Qwen3-30B-A3B and Ministral-3-14B on
an L4).

This cookbook:

- Defines **each model as a first-class Podman Quadlet**, instantiated from a
  single **templated** unit `vllm-model@.container` → `vllm-model@<model>.service`
  (e.g. `vllm-model@qwen05.service`) that references a shared `vllm.image`. Every
  model parameter lives in a per-model engine config (`models/<model>.yaml`), so
  the instances differ only by their fixed loopback port (a small per-instance
  drop-in). The models are **not** started at boot: llmsnap owns their lifecycle.
- Runs **llmsnap as a containerized, non-root control plane** (`llmsnap.container`,
  `User=10032`, `Network=host`, bound to the **host loopback** `127.0.0.1:8000`).
  The image is built locally (`llmsnap.build`) from the version-pinned,
  checksum-verified llmsnap release. llmsnap no longer runs `podman` or touches
  the GPU: it only **starts/stops the model units over the host D-Bus system bus**
  (`systemctl start/stop vllm-model@<model>.service`) and swaps between them via
  sleep/wake.
- Grants that non-root control plane the right to manage **only** the
  `vllm-*.service` units through a **polkit rule**.
  Everything else on the host stays off-limits.
- Publishes the service through **Traefik** (requires the `traefik` cookbook),
  which terminates TLS with an automatic Let's Encrypt certificate, authenticates
  callers by **API key** (`Authorization: Bearer`, via the
  `api-key-and-token-middleware` community plugin) and applies a strict `/v1/*`
  path allowlist (`other/traefik/vllm.yaml`).

> This is designed for a remote gateway (e.g. a separate LiteLLM host) to consume
> the models over the network, while llmsnap itself never leaves the loopback.

## Privilege model (models rootful, llmsnap not)

The **vLLM models run rootful**: accessing the NVIDIA GPU through CDI
(`--device nvidia.com/gpu=all`) together with `--security-opt label=disable`
requires root privileges, similar to the `samba` and `vsftpd` cookbooks. Each
`vllm-model@<model>.service` is a rootful Podman container started by systemd.

**llmsnap itself runs unprivileged.** Because the models are separate units,
llmsnap needs neither `podman` nor the GPU — it is a pure control plane. It runs
as a **non-root container** (`User=10032`, `DropCapability=ALL`, `ReadOnly=true`,
`NoNewPrivileges`) whose only host reach is the D-Bus system-bus socket. A scoped
**polkit rule** lets uid 10032 start/stop `vllm-*.service` and nothing else.

> `SecurityLabelDisable=true` is set on `llmsnap.container` only so the confined
> container can reach the host D-Bus socket (SELinux `container_t` → `system_dbusd_t`).
> The privilege boundary is the non-root uid + the scoped polkit rule, not SELinux
> confinement.

## Prerequisites

- The `base` and `traefik` cookbooks (installed automatically as dependencies).
  `base` provides the fedora base image used to build the llmsnap control-plane
  image.
- A working **systemd + D-Bus + polkit** host (the default on Fedora CoreOS). The
  containerized, non-root llmsnap drives the model units over the D-Bus system bus.
- An **NVIDIA GPU** with the driver + Container Toolkit and a working CDI spec at
  `/etc/cdi/nvidia.yaml` (`nvidia.com/gpu=all`) — for the production (GPU) config.
  This is host-level setup, out of scope of this cookbook. The shipped **CPU
  smoke-test** config needs no GPU. **On a GPU-less VM the CPU models launch and
  answer** (slowly); the CUDA production config is documented in `SPECS.md`.
- Configuration files provided by the user (copied from the examples):
  - `/etc/quadlets/vllm/config.yaml` — the llmsnap model definitions.
  - `/etc/quadlets/vllm/models/<name>.yaml` — the vLLM engine configuration for
    each model (`vllm serve --config`).
  - `/etc/quadlets/vllm/vllm.env` — secrets (`HF_TOKEN`) injected into vLLM.
- Traefik must expose an `https` entryPoint and a `le` (Let's Encrypt)
  `certificatesResolver`, and declare the `traefik-api-token-middleware` plugin
  in its static config (`experimental.plugins`) — all provided by the traefik
  cookbook example config. See `other/traefik/vllm.yaml` and the traefik cookbook.

## Configuration

- `config.yaml` — llmsnap configuration. Each model entry no longer holds a
  `podman run` line; it holds a **`proxy:`** (the fixed loopback port its Quadlet
  publishes) and a **`cmd:`/`cmdStop:`** that only `systemctl start/stop` the
  matching `vllm-model@<model>.service` (with a foreground `is-active` bridge —
  see the header of the shipped `config.yaml`). The sleep/wake endpoints and the
  swap group are unchanged. See <https://github.com/napmany/llmsnap>.

  > **Adding/editing a model:** the model unit itself is a single templated
  > Quadlet (`vllm-model@.container`), so you do **not** copy a whole container
  > file. For a new model `<name>` you only add three small pieces:
  >
  > 1. `models/<name>.yaml` — its vLLM engine config (see below).
  > 2. `models/<name>.env` — its own fixed host-loopback API port
  >    `COOKBOOK_VLLM_MODEL_PORT=58NN` (fed to vLLM's `--host 127.0.0.1 --port`
  >    by the shared template; the unit runs `Network=host`, so there is no
  >    `PublishPort`). Do **not** call it `VLLM_PORT`: that variable is vLLM's
  >    internal port, not the API port.
  > 3. an entry in `config.yaml` with `proxy: http://127.0.0.1:58NN` and the
  >    `systemctl … vllm-model@<name>.service` `cmd`/`cmdStop`.
  >
  > Keep the port in sync across `models/<name>.env` and `config.yaml`.

- `models/<name>.yaml` — the **vLLM engine configuration** for one model
  (`model:`, `served-model-name:`, `dtype:`, `max-model-len:`, …). Each model
  Quadlet mounts its file read-only at `/etc/vllm/config.yaml` and runs
  `vllm serve --config …`, so every engine parameter lives here rather than on
  the container command line. Keys are the long CLI flags with the leading `--`
  stripped; store-true flags (e.g. `--enforce-eager`) become `true`. See
  <https://docs.vllm.ai/en/latest/configuration/serve_args.html>.

  > **Architecture note (GPU):** the CUDA image tag is architecture-specific
  > (`:v0.24.0-aarch64` for arm64, `:v0.24.0` for amd64). Set the `VLLM_IMAGE` environment
  > variable in `vllm.env` to match your host.
  > The shipped `vllm.image` uses the multi-arch CPU smoke-test image.

- `vllm.env` — secrets injected into every vLLM container as environment
  variables (installed `0600 root:root`):

  | Variable   | Purpose                                       |
  | ---------- | --------------------------------------------- |
  | `HF_TOKEN` | Hugging Face token to download model weights  |

- `other/traefik/vllm.yaml` — Traefik router + the `vllm-api-token` middleware.
  Edit the `Host(...)` FQDN and replace the placeholder API keys in the
  middleware `tokens:` list (raw tokens, without the `Bearer ` prefix). Generate
  a key with `echo "sk-$(openssl rand -hex 32)"`.

## Data

- `/var/lib/quadlets/vllm/cache` — Hugging Face weights cache. Re-downloadable, so
  it is stored under `/var/lib/quadlets` (non-precious) and created by
  `tmpfiles.d/vllm.conf`.

## Ports

- TCP `8000` — llmsnap, bound on `127.0.0.1` only, exposed through Traefik.
- TCP `5801`, `5802`, … — fixed vLLM model ports (host loopback, one per model,
  published by each model's `vllm-model@<model>.container.d` port drop-in and referenced by `proxy:` in
  `config.yaml`).
- TCP `443` — public HTTPS ingress (Traefik).

## UID / GID

- **llmsnap** control plane: uid/gid **10032** (non-root `vllm` container +
  system user; see "Privilege model" above).
- **vLLM models**: `root` (rootful Podman for GPU/CDI access).

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the cookbook (installs `base`, `traefik`, builds the llmsnap image,
installs the polkit rule and starts `vllm.target`).

```sh
sudo make clean install
```

Check that llmsnap is up (once a model is awake):

```sh
curl -sSf http://127.0.0.1:8000/v1/models
```

Then, through Traefik with a valid API key:

```sh
curl -sSf -H 'Host: vllm' http://127.0.0.1/v1/models -H "Authorization: Bearer secret123"
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```
