"""Fresh-install tests for the NetBird control plane.

The test ignition (fcos-test.ign) contains the cookbook and its dependencies but NOT the
examples or the dependency hooks (both are excluded from the production package). So this
module injects, via ``fcos_extra_files``:

  * the PostgreSQL server config (config.env) — otherwise postgresql never starts and
    management loops waiting for the database,
  * the operator-provided NetBird config (read from this cookbook's own config/examples/),
  * the PostgreSQL init hook that creates the netbird database (other/postgresql/netbird.sql),
  * the Traefik routing hook (other/traefik/netbird.yaml) and a minimal Traefik main config.

The tests are self-sufficient: they assert what holds without a working OIDC provider (units
active, ports listening, generated config in place, database reachable, Traefik routing to the
right backend). They do not attempt a login flow.
"""

import subprocess
import textwrap
from pathlib import Path

import pytest

from helpers import TestNetbird

COOKBOOK_DIR = Path(__file__).resolve().parent.parent

# PostgreSQL server config for the dependency. config.env ships only as an example (excluded
# from the test ignition), so it must be injected or postgresql.target never comes up.
POSTGRESQL_CONFIG_ENV = textwrap.dedent("""\
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_DB=postgres
    POSTGRES_HOST_AUTH_METHOD=scram-sha-256
    POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256
    POSTGRES_ARGS=-h 127.0.0.1
    PGPORT=5432
    PG_MAJOR=18
    POSTGRES_BACKUP_RETENTION=7
""")

# Minimal Traefik main configuration: a file provider watching conf.d and the two entry
# points. TLS is served self-signed (the netbird.yaml routers use bare `tls: {}`), so no ACME
# / certificate resolver is needed for the tests.
TRAEFIK_YAML = """\
api:
  dashboard: false
# The traefik cookbook ships a packaged conf.d/ping.yaml that references ping@internal;
# enable manualRouting so that router loads cleanly.
ping:
  manualRouting: true
log:
  level: INFO
accesslog: false
global:
  sendanonymoususage: false
  checknewversion: false
entryPoints:
  http:
    address: ":80"
  https:
    address: ":443"
providers:
  file:
    directory: /etc/traefik/conf.d/
    watch: true
"""


def _read(rel: str) -> str:
    return (COOKBOOK_DIR / rel).read_text()


@pytest.fixture(scope="package")
def fcos_vm_config() -> tuple[int, int, int, int]:
    """More resources: five NetBird images plus PostgreSQL and Traefik to pull and start."""
    return (6144, 4, 50, 100)


@pytest.fixture(scope="module")
def fcos_extra_files() -> dict:
    """Inject operator config + dependency config/hooks that the test ignition does not carry."""
    return {
        # PostgreSQL server config (dependency): without it postgresql.target never starts.
        "/etc/quadlets/postgresql/config.env": (POSTGRESQL_CONFIG_ENV, 0, 0, 0o600),
        # Traefik main config + the routing hook shipped by this cookbook.
        "/etc/quadlets/traefik/traefik.yaml": (TRAEFIK_YAML, 10001, 10000, 0o644),
        "/etc/quadlets/traefik/conf.d/netbird.yaml": (_read("other/traefik/netbird.yaml"), 10001, 10000, 0o644),
        # PostgreSQL init hook: creates the netbird database/user on first boot.
        "/etc/quadlets/postgresql/init.d/netbird.sql": (_read("other/postgresql/netbird.sql"), 10004, 10000, 0o600),
        # Operator-provided NetBird config (working-but-insecure examples).
        "/etc/quadlets/netbird/management.json": (_read("config/examples/management.json"), 10035, 10000, 0o640),
        "/etc/quadlets/netbird/management.env": (_read("config/examples/management.env"), 0, 0, 0o600),
        "/etc/quadlets/netbird/dashboard.env": (_read("config/examples/dashboard.env"), 0, 0, 0o600),
        "/etc/quadlets/netbird/relay.env": (_read("config/examples/relay.env"), 0, 0, 0o600),
        "/etc/quadlets/netbird/turnserver.conf": (_read("config/examples/turnserver.conf"), 10035, 10000, 0o640),
    }


class TestNetbirdInstall(TestNetbird):
    """Verify the NetBird control plane comes up cleanly on a fresh VM boot."""

    def test_management_connected_to_postgres(self, fcos_host):
        """Management must have selected the Postgres store engine and not be crash-looping."""
        result = fcos_host.run("podman logs netbird-management 2>&1 | grep -i 'Postgres store engine'")
        assert result.rc == 0, "management did not report using the Postgres store engine"
        restarts = fcos_host.run("systemctl show -p NRestarts --value netbird-management.service")
        assert restarts.stdout.strip() == "0", f"management restarted {restarts.stdout.strip()} times"

    def test_netbird_database_exists(self, fcos_host):
        """The postgresql hook must have created the netbird database."""
        result = fcos_host.run(
            "podman exec postgresql-server psql -U postgres -tAc "
            "\"SELECT 1 FROM pg_database WHERE datname='netbird'\""
        )
        assert result.stdout.strip() == "1", f"netbird database missing: {result.stdout} {result.stderr}"

    def test_dashboard_served_through_traefik(self, fcos_vm):
        """Traefik must serve the dashboard SPA over HTTPS (self-signed) on the netbird host."""
        result = subprocess.run(
            ["curl", "-sS", "-k", "-o", "/dev/null", "-w", "%{http_code}",
             "--resolve", f"netbird:443:{fcos_vm.ip}", "https://netbird/"],
            check=False, capture_output=True, text=True,
        )
        assert result.stdout.strip() == "200", f"dashboard not served: got {result.stdout!r} {result.stderr}"

    def test_management_api_reachable_through_traefik(self, fcos_vm):
        """Traefik must route /api to management (401 = reached and demands auth, not 502)."""
        result = subprocess.run(
            ["curl", "-sS", "-k", "-o", "/dev/null", "-w", "%{http_code}",
             "--resolve", f"netbird:443:{fcos_vm.ip}", "https://netbird/api/users"],
            check=False, capture_output=True, text=True,
        )
        assert result.stdout.strip() == "401", f"/api not routed to management: got {result.stdout!r}"

    def test_relay_reachable_through_traefik(self, fcos_vm):
        """Traefik must route /relay to the relay (426 = WebSocket upgrade required, not 502)."""
        result = subprocess.run(
            ["curl", "-sS", "-k", "-o", "/dev/null", "-w", "%{http_code}",
             "--resolve", f"netbird:443:{fcos_vm.ip}", "https://netbird/relay"],
            check=False, capture_output=True, text=True,
        )
        assert result.stdout.strip() == "426", f"/relay not routed to relay: got {result.stdout!r}"
