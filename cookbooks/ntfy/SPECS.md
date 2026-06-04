# Specification for ntfy Quadlet Cookbook

You will have to develop a Quadlet cookbook for ntfy.sh, the self-hosted notification server.

## Architecture

Ntfy is a web application, deployed as a container image, available here: `docker.io/binwiederhier/ntfy:v2`.

Ntfy relies on a PostgreSQL database to store its data. It also uses a cache directory for attachments (that you have to store on virtiofs).
You will also have to expose it through Traefik.

## Common requirements

- Each docker image MUST have its quadlet .image file.
- Each cookbook MUST have a dedicated unique UID. The GID is 10000.
- Persistent data MUST be stored on virtiofs (`/var/lib/virtiofs/data/ntfy`).

## Sample commands for deployment

You will have to convert the following command to a Quadlet recipe:

```sh
docker run -v /etc/ntfy:/etc/ntfy -v /var/cache/ntfy:/var/cache/ntfy -e TZ=UTC -p 8080:8080 -u $UID:$GID -it binwiederhier/ntfy serve
```

Other example, using Docker Compose:

```yaml
services:
  ntfy:
    image: binwiederhier/ntfy
    container_name: ntfy
    command:
      - serve
    environment:
      - TZ=UTC    # optional: set desired timezone
    user: $UID:$GID # optional: replace with your own user/group or uid/gid
    volumes:
      - /var/cache/ntfy:/var/cache/ntfy
      - /etc/ntfy:/etc/ntfy
    ports:
      - 8080:8080
    healthcheck: # optional: remember to adapt the host:port to your environment
        test: ["CMD-SHELL", "wget -q --tries=1 http://localhost:8080/v1/health -O - | grep -Eo '\"healthy\"\\s*:\\s*true' || exit 1"]
        interval: 60s
        timeout: 10s
        retries: 3
        start_period: 40s
    restart: unless-stopped
    init: true # needed, if healthcheck is used. Prevents zombie processes
```

## Security

Directly set the UID and GID in the quadlet file (no mapping).
Use the host network, like other quadlet cookbooks.
Let's Encrypt certificates will be handled by Traefik, so no need to worry about that in the ntfy cookbook.

## Configuration

The configuration file for ntfy (`/etc/ntfy/server.yml` inside the container) is in YAML format.

```yaml
# Server
base-url: "https://ntfy.itix.fr"
behind-proxy: true
listen-http: "127.0.0.1:8080"

# Database
database-url: "postgres://user:pass@host:5432/ntfy"

# Access control
auth-default-access: "deny-all"
auth-users:
  # fields are: login:bcrypt-hashed-password:role (admin or user)
  - "admin:$2b$REDACTED:admin"
enable-login: true
require-login: true

# Attachments
attachment-cache-dir: "/var/cache/ntfy/attachments"
attachment-file-size-limit: "100M"
attachment-total-size-limit: "50G"
attachment-expiry-duration: "48h"

# Message cache
cache-duration: "48h"

# Upstream
upstream-base-url: "https://ntfy.sh"
```

## Useful examples

You can copy the structure of the `miniflux` cookbook, which is also a web application relying on a database and exposed through Traefik.
For virtiofs persistent storage, have a look at the `redis` or `postgresql` cookbooks.

## Useful links

- [Installation guide](https://ntfy.sh/docs/install/)
- [Configuration reference](https://ntfy.sh/docs/config/)
