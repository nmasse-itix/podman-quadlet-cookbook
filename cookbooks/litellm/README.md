# Podman Quadlet: LiteLLM

## Overview

[LiteLLM](https://docs.litellm.ai/) is an LLM gateway (proxy server) that exposes
100+ LLM providers behind a single, OpenAI-compatible API, with authentication,
budgets, rate limiting and a management UI.

This cookbook:

- Runs LiteLLM in **proxy mode** using the **non-root** container image
  (`ghcr.io/berriai/litellm-non_root`), which runs as UID/GID `65534`.
  UID/GID mapping remaps it to the dedicated `litellm` user (`10024`) and the
  `itix-svc` group (`10000`) on the host.
- Reads its behaviour from a configuration file (`config.yaml`).
- Reads secrets and passwords (master key, UI credentials, database URL) from a
  separate `config.env` file injected as environment variables.
- Redirects the root path (`/`) to the Admin UI (`/ui`) and serves the API docs
  under `/docs`.
- Uses PostgreSQL as its backend (requires the `postgresql` cookbook) to persist
  keys, models and spend logs.
- Is published through Traefik (requires the `traefik` cookbook).

## Prerequisites

- The `postgresql` cookbook must be installed and running.
- The `traefik` cookbook must be installed and running.
- Configuration files `/etc/quadlets/litellm/config.yaml` and
  `/etc/quadlets/litellm/config.env` must exist (copied from the examples).

## Configuration

- `config.yaml` — proxy configuration (`model_list`, `general_settings`, ...).
  See <https://docs.litellm.ai/docs/proxy/config_settings>.
- `config.env` — secrets injected as environment variables:

  | Variable             | Purpose                                         |
  | -------------------- | ----------------------------------------------- |
  | `LITELLM_MASTER_KEY` | Master key for the proxy (must start with `sk-`)|
  | `UI_USERNAME`        | Username to sign in on the Admin UI             |
  | `UI_PASSWORD`        | Password to sign in on the Admin UI             |
  | `DATABASE_URL`       | PostgreSQL connection string                    |

  The root redirect (`ROOT_REDIRECT_URL=/ui`) and docs path (`DOCS_URL=/docs`)
  are set directly in the Quadlet file.

## Ports

- TCP `4000`: LiteLLM proxy / Admin UI (bound on `127.0.0.1`, exposed through
  Traefik).

## UID / GID

- User `litellm`: UID `10024`
- Group `itix-svc`: GID `10000`
- Inside the container the process runs as `65534:65534` (mapped to the host
  IDs above).

## Usage

In a separate terminal, follow the logs.

```sh
sudo make tail-logs
```

Install the Podman Quadlets and start LiteLLM.

```sh
sudo make clean install
```

You should see the **litellm.service** waiting for PostgreSQL to be available,
then running its database migrations and starting up.

Verify LiteLLM is running using its liveness endpoint:

```sh
curl -sSf http://127.0.0.1:4000/health/liveliness
```

Then browse to the service through Traefik (the root path redirects to `/ui`):

```sh
curl --resolve litellm:80:127.0.0.1 -L http://litellm/
```

Finally, remove the quadlets, their configuration and their data.

```sh
sudo make uninstall clean
```
