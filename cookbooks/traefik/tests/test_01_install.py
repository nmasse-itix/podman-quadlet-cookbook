import textwrap
import test_quadlet  # noqa: F401
import pytest
import subprocess
import tempfile
from pathlib import Path

@pytest.fixture(scope="module")
def dns_names() -> list[str]:
    """List of DNS names to be resolved by the VM (e.g. for ACME challenges)."""
    return [ "secure", "ping" ]

# Extra files to inject into the FCOS image for the tests in this file.
@pytest.fixture(scope="module")
def fcos_extra_files(pebble_acme_server, top_level_domain) -> dict:
    """
    Extra files to inject into the FCOS VM image.
    """

    files = {
        # Exposes the Traefik ping endpoint to localhost.
        "/etc/quadlets/traefik/conf.d/ping.yaml": (
            textwrap.dedent(f"""\
                http:
                    routers:
                        traefik-ping:
                            rule: Host(`ping`) || Host(`ping.{top_level_domain}`)
                            entryPoints:
                            - http
                            service: "ping@internal"
                            middlewares:
                            - localhost-only
                    middlewares:
                        localhost-only:
                            ipAllowList:
                                sourceRange:
                                - "127.0.0.1/32"
            """),
            10001,
            10000,
            0o644,
        ),
        # Exposes the ping endpoint to the outside world over HTTPS only
        "/etc/quadlets/traefik/conf.d/secure.yaml": (
            textwrap.dedent(f"""\
                http:
                    routers:
                        secure:
                            rule: Host(`secure.{top_level_domain}`)
                            entryPoints:
                            - https
                            service: "ping@internal"
                            tls:
                              certResolver: le
            """),
            10001,
            10000,
            0o644,
        ),
        # The Pebble CA certificate is needed for Traefik to trust the Pebble ACME server.
        "/etc/quadlets/traefik/pebble.pem": (
            pebble_acme_server['ca_cert'],
            10001,
            10000,
            0o644,
        ),
        # The main Traefik configuration file.
        "/etc/quadlets/traefik/traefik.yaml": (
            textwrap.dedent(f"""\
                api:
                  dashboard: false
                  debug: false
                ping:
                  manualRouting: true

                log:
                  level: "INFO"

                accesslog: false

                global:
                  sendanonymoususage: false
                  checknewversion: false

                entryPoints:
                  http:
                    address: ":80"
                  https:
                    address: ":443"

                certificatesResolvers:
                  le:
                    acme:
                      email: "traefik@{top_level_domain}"
                      caServer: "{pebble_acme_server['directory_url']}"
                      caCertificates: "/etc/traefik/pebble.pem"
                      keyType: "EC384"
                      httpChallenge:
                        entryPoint: http
                      storage: "/var/lib/traefik/acme.json"

                providers:
                  file:
                    directory: /etc/traefik/conf.d/
                    watch: true
                """),
            10001,
            10000,
            0o644,
        ),
    }
    
    return files

"""
Verify that the Traefik Quadlet is correctly installed and configured on a fresh VM boot.
"""
class TestTraefikQuadlet(test_quadlet.TestQuadlet):
    expected_services = [
        { "name": "traefik.target", "state": "active", "exists": True },
        { "name": "traefik.service", "state": "active", "exists": True },
    ]

    expected_sockets = [
        { "uri": "tcp://127.0.0.1:80", "state": "listening" },
        { "uri": "tcp://127.0.0.1:443", "state": "listening" },
    ]

    expected_ports = [
        { "number": 80, "protocol": "tcp", "state": "open" },
        { "number": 443, "protocol": "tcp", "state": "open" },
        { "number": 22, "protocol": "tcp", "state": "open" },
    ]

    expected_files = [
        { "path": "/var/lib/quadlets/traefik", "type": "directory", "owner": "traefik", "group": "itix-svc", "mode": 0o755 },
        { "path": "/etc/quadlets/traefik", "type": "directory", "owner": "traefik", "group": "itix-svc", "mode": 0o755 },
        { "path": "/etc/quadlets/traefik/traefik.yaml", "type": "file", "owner": "traefik", "group": "itix-svc", "mode": 0o644 },
    ]

    expected_podman_images = [
        { "name": "docker.io/library/traefik", "tag": "v3.4", "state": "present" },
    ]

    expected_podman_containers = [
        { "name": "traefik", "state": "present", "pid1": { "owner": "10001", "group": "10000" } },
    ]

    expected_main_service = "traefik.target"
    expected_main_service_timeout = 300

    @pytest.mark.flaky(reruns=6, reruns_delay=5)
    def test_traefik_ping_localhost(self, fcos_host):
        """Traefik must respond to the ping endpoint with HTTP 200."""
        result = fcos_host.run("curl -sSf -o /dev/null -w '%{http_code}' -H 'Host: ping' http://127.0.0.1/")
        assert result.rc == 0, f"curl failed with exit code {result.rc}: {result.stderr}"
        assert result.stdout.strip() == "200", f"Expected HTTP 200 from ping endpoint, got: {result.stdout.strip()}"

    def test_traefik_reject_ping_external(self, fcos_vm, top_level_domain):
        """Traefik must NOT respond to the ping endpoint outside localhost."""
        result = subprocess.run(
            [
                "curl",
                "-sSf",
                "-o", "/dev/null",
                "--resolve", f"ping.{top_level_domain}:80:{fcos_vm.ip}",
                "-w", "%{http_code}",
                f"http://ping.{top_level_domain}/"
            ],
            check=False,
            capture_output=True,
        )
        assert result.returncode == 22, f"curl failed with exit code {result.returncode}: {result.stderr}"
        assert int(result.stdout.strip()) == 403, f"Expected HTTP 403 from ping endpoint, got: {result.stdout.strip()}"

    # This test is flaky because it depends on ACME certificate issuance, which can take time.
    # During ACME certificate issuance, Traefik responds with a self-signed certificate which causes curl to fail with a certificate error.
    # We work around this by retrying the test several times with a delay between retries.
    @pytest.mark.flaky(reruns=12, reruns_delay=5)
    def test_traefik_tls(self, fcos_vm, pebble_acme_server, top_level_domain):
        """Traefik must respond to the secure endpoint with HTTP 200."""

        # Store the Pebble CA bundle in a temporary file so that curl can use it to verify the certificate presented by Traefik.
        tmpdir = tempfile.TemporaryDirectory(delete=True)
        d = Path(tmpdir.name)
        pebble_ca_bundle_path = d / "pebble.pem"
        pebble_ca_bundle_path.write_text(pebble_acme_server['ca_bundle'])

        result = subprocess.run(
            [
                "curl",
                "-sSf",
                "-o", "/dev/null",
                "--cacert", str(pebble_ca_bundle_path),
                "--resolve", f"secure.{top_level_domain}:443:{fcos_vm.ip}",
                "-w", "%{http_code}",
                f"https://secure.{top_level_domain}/"
            ],
            check=False,
            capture_output=True,
        )
        assert result.returncode == 0, f"curl failed with exit code {result.returncode}: {result.stderr}"
        assert int(result.stdout.strip()) == 200, f"Expected HTTP 200 from ping endpoint, got: {result.stdout.strip()}"

    def test_traefik_restart(self, fcos_host):
        """Restarting traefik.target must keep Traefik running and the ping endpoint must still respond."""
        result = fcos_host.run("systemctl restart traefik.target")
        assert result.rc == 0, f"Failed to restart traefik.target: {result.stderr}"

        # Wait for traefik.target to become active again after the restart
        self.wait_for_service(fcos_host, "traefik.target", timeout=120)

        # traefik.service must still be running after the restart
        self.check_expected_services(fcos_host, [
            { "name": "traefik.service", "state": "active", "exists": True },
        ])

        # Ping endpoint must still respond after the restart
        result = fcos_host.run("curl -sSf -H 'Host: ping' http://127.0.0.1/")
        assert result.rc == 0, f"curl failed after restart: {result.stderr}"
    
