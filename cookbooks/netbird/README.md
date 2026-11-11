# NetBird (control plane)

[NetBird](https://netbird.io/) is an open-source, self-hostable WireGuard-based overlay
network. This cookbook deploys the **control plane** as separate containers, following the
advanced (multi-container) self-hosted layout, so it can be pointed at an **external OpenID
Connect identity provider**.

Components:

| Container | Image | Role |
|-----------|-------|------|
| `netbird-management` | `netbirdio/management` | Management API + gRPC (peer configuration, store) |
| `netbird-signal` | `netbirdio/signal` | Signal exchange (peer connection setup) |
| `netbird-relay` | `netbirdio/relay` | Relay for peers that cannot connect directly |
| `netbird-dashboard` | `netbirdio/dashboard` | Web UI (SPA) |
| `netbird-coturn` | `coturn/coturn` | STUN/TURN server (NAT traversal) |

> **Scope.** This cookbook is the control plane only. The NetBird **agent** (peers, routing
> peers) is out of scope. It does **not** bundle an identity provider: the management service
> and the dashboard point at an external OIDC provider that the operator configures.

## Prerequisites

### Dependencies (installed automatically)

- **`postgresql`** — the management store. The `other/postgresql/netbird.sql` hook creates
  the `netbird` database and user. PostgreSQL handles major upgrades and backups.
- **`traefik`** — TLS termination and HTTP/gRPC/WebSocket ingress on port 443. The
  `other/traefik/netbird.yaml` hook wires the routing. NetBird must **not** obtain its own
  certificates (`LETSENCRYPT_DOMAIN=none`); Traefik owns TLS.

The `keycloak` cookbook of this repository is **not** a dependency (that would force it onto
every install). It is one valid way to provide the external OIDC provider — see below.

### virtiofs mounts

- `/var/lib/virtiofs/data/netbird` — precious data (the management data directory, which
  holds key material peers pin). The management **store** itself lives in PostgreSQL.

### Resources (control plane, small deployment)

- **CPU:** 2 vCPU.
- **RAM:** ~1 GiB for the NetBird containers (PostgreSQL and Traefik are extra; budget ~2 GiB
  total on the VM).
- **Disk:** a few hundred MiB for images; the store grows with the number of peers (tens of
  MiB for hundreds of peers). coturn relays media through RAM/network, not disk.

## Files the operator must provide

All live under `/etc/quadlets/netbird/`. Working-but-insecure examples ship under
`config/examples/` (installed by `make install` and by the dev VM, **not** part of the
production package). `netbird.target` and each unit are gated with `ConditionPathExists`, so a
VM built from the ignition file before these are pushed stays idle instead of crash-looping.

| File | Mode / owner | Contents |
|------|--------------|----------|
| `management.json` | `0640` `netbird:itix-svc` | Management config: OIDC, STUN/TURN, relay, signal, data-store encryption key, store engine. Keystone that gates the target. |
| `management.env` | `0600` `root:root` | `NETBIRD_STORE_ENGINE_POSTGRES_DSN` (PostgreSQL DSN incl. DB password). |
| `dashboard.env` | `0600` `root:root` | Dashboard OIDC client + `NETBIRD_MGMT_API_ENDPOINT` + `LETSENCRYPT_DOMAIN=none`. |
| `relay.env` | `0600` `root:root` | `NB_LISTEN_ADDRESS`, `NB_EXPOSED_ADDRESS`, `NB_AUTH_SECRET`. |
| `turnserver.conf` | `0640` `netbird:itix-svc` | coturn config: TURN user/password, realm, and (behind NAT) `external-ip`. |

Values that must stay consistent across files:

- **DB password:** `management.env` DSN ↔ `other/postgresql/netbird.sql`.
- **TURN password:** `turnserver.conf` `user=self:<pw>` ↔ `management.json` `TURNConfig.Turns[].Password`.
- **Relay secret:** `relay.env` `NB_AUTH_SECRET` ↔ `management.json` `Relay.Secret`.
- **Data-store encryption key:** `management.json` `DataStoreEncryptionKey` — 32 bytes,
  base64-encoded (`openssl rand -base64 32`). Losing or changing it makes encrypted store
  fields unreadable; treat it as precious.

### OIDC settings the operator must fill in

The control plane needs an external OIDC provider. The `keycloak` cookbook of this repository
is one way to provide it (create a realm, a public PKCE client for the dashboard, and — if you
want NetBird to manage users in the IdP — a confidential client); or point at any provider you
run elsewhere. Fill in:

- **`management.json` → `HttpConfig`:** `AuthIssuer` (issuer URL), `AuthAudience`,
  `AuthKeysLocation` (JWKS URL), and `OIDCConfigEndpoint` (the provider's
  `.well-known/openid-configuration`).
- **`management.json` → `PKCEAuthorizationFlow.ProviderConfig`:** `ClientID`, `Audience`,
  `AuthorizationEndpoint`, `TokenEndpoint`, `Scope`, `RedirectURLs`.
- **`dashboard.env`:** `AUTH_AUTHORITY`, `AUTH_CLIENT_ID`, `AUTH_AUDIENCE`,
  `AUTH_SUPPORTED_SCOPES` (and `AUTH_CLIENT_SECRET` if your client is confidential).

> The shipped example leaves `OIDCConfigEndpoint` **empty** on purpose: management then boots
> without contacting a provider (JWKS is fetched lazily), which keeps `make install` and the
> tests self-sufficient. **In production set `OIDCConfigEndpoint`** (or at least a correct
> `AuthKeysLocation`) to your provider, otherwise tokens cannot be validated.
>
> `IdpManagerConfig.ManagerType` is `none` in the example. Set it (e.g. `keycloak`) with IdP
> admin client credentials only if you want NetBird to manage users in the provider.

## Ports

The consumer maintains the Internet-facing firewall by hand. Only these must be reachable
**from the Internet**:

| Port | Proto | Where | Why |
|------|-------|-------|-----|
| 443 | TCP | Traefik | Dashboard, management API + gRPC, signal gRPC, relay — all multiplexed on one host name (NetBird 0.29+ shares 443 via HTTP/2; Traefik dispatches by path prefix, gRPC over h2c). |
| 3478 | UDP (and TCP) | coturn | STUN/TURN. **Cannot** go through an HTTP reverse proxy. |
| 49152–65535 | UDP | coturn | TURN relayed-media port range. **Cannot** go through an HTTP reverse proxy. Keep in sync with `min-port`/`max-port` in `turnserver.conf`. |

Backend ports used **behind Traefik / on the host only** (must **not** be exposed to the
Internet):

| Port | Proto | Service | Bind |
|------|-------|---------|------|
| 8080 | TCP | dashboard (nginx) | `127.0.0.1` only (published from the container namespace) |
| 33073 | TCP | management (HTTP API + gRPC, h2c) | host |
| 10000 | TCP | signal (gRPC + WebSocket proxy, h2c) | host |
| 33080 | TCP | relay (WebSocket) | host |
| 9090 / 9092 / 9093 | TCP | management / signal / relay Prometheus metrics | host |
| 9000 | TCP | relay health check | host |

## UID and GID

Runs as **UID 10035** (`netbird`) / **GID 10000** (`itix-svc`).

- `management`, `signal`, `relay` run as `10035:10000` under host networking.
- `coturn` runs as `10035:10000` under host networking with `CAP_NET_BIND_SERVICE` (to bind
  the privileged port 3478), the same pattern as the `traefik` cookbook.
- `dashboard` uses the upstream rootful image, which serves the SPA with nginx on port 80 and
  ships no configurable HTTP port. Rather than fork it, it runs in its own network namespace
  (not host networking) so nginx keeps port 80 inside the container, and the port is published
  only on `127.0.0.1:8080` for Traefik. The rootful image is mapped to the non-root host UID
  `10035` via `UIDMap`/`GIDMap` (the same approach as the `nextcloud` cookbook), so no process
  runs as root on the host.

## Notes

- The management schema is migrated by the management process itself on start, so there is no
  separate init/migration unit.
- coturn behind NAT: set `external-ip` in `turnserver.conf` so relayed addresses are correct.
- TLS on coturn (5349) is disabled; NetBird uses STUN/TURN over 3478 with long-term
  credentials. Enabling it would require certificates this cookbook does not manage.
