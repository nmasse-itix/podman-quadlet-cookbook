import subprocess
import textwrap
import time
import test_quadlet  # noqa: F401
import pytest
import testinfra

CERT_DIR = "/var/lib/quadlets/lego/certificates"
CERT_PATH = f"{CERT_DIR}/default.crt"
KEY_PATH = f"{CERT_DIR}/default.key"
LEGO_CONFIG = "/etc/quadlets/lego/lego.yaml"
HOOK_MARKER = "/tmp/lego-hook-executed"


def prime_dns_cache(dns_server_ip: str, names: list[str]) -> None:
    """Workaround for flaky ACME validations in the test environment.

    Pebble resolves the domains over TCP. When the libvirt dnsmasq has to forward the AAAA
    query of a test domain upstream over TCP, the query may time out. A UDP query puts the
    (negative) answer in the dnsmasq cache, so that the subsequent TCP query of Pebble succeeds.
    """
    for name in names:
        for qtype in ("A", "AAAA"):
            subprocess.run(["dig", "+time=2", "+tries=2", qtype, f"@{dns_server_ip}", name], capture_output=True)


@pytest.fixture(scope="module")
def dns_names() -> list[str]:
    """lego domain must be DNS-resolvable so Pebble can reach the VM on port 80 for HTTP-01 validation."""
    return ["lego"]


@pytest.fixture(scope="module")
def fcos_extra_files(pebble_acme_server, top_level_domain) -> dict:
    """Extra files to inject into the FCOS VM for lego tests."""
    return {
        # Lego configuration pointing at the Pebble ACME test server.
        LEGO_CONFIG: (
            textwrap.dedent(f"""\
                storage: /var/lib/lego
                log:
                  format: text
                accounts:
                  default:
                    server: {pebble_acme_server['directory_url']}
                    email: test@{top_level_domain}
                    acceptsTermsOfService: true
                challenges:
                  http:
                    http:
                      address: ":80"
                certificates:
                  default:
                    account: default
                    challenge: http
                    domains:
                      - lego.{top_level_domain}
                    renew:
                      disableRandomSleep: true
                hooks:
                  deploy:
                    command: /bin/sh /etc/lego/deploy-hook.sh
            """),
            10023,  # owner: lego
            10000,  # group: itix-svc
            0o644,
        ),
        # Pebble root CA certificate, needed by lego to authenticate the Pebble ACME server.
        "/etc/quadlets/lego/pebble.pem": (
            pebble_acme_server["ca_cert"],
            0,      # owner: root
            0,      # group: root
            0o644,
        ),
        # Drop-in to trust the Pebble CA.
        "/etc/containers/systemd/lego.container.d/pebble.conf": (
            textwrap.dedent("""\
                [Container]
                Environment=LEGO_CA_CERTIFICATES=/etc/lego/pebble.pem
            """),
            0,      # owner: root
            0,      # group: root
            0o644,
        ),
        # Test hook: creates a marker file to verify that process-hooks.sh calls it.
        "/etc/quadlets/lego/renew-hooks.d/test-hook.sh": (
            textwrap.dedent(f"""\
                #!/bin/sh
                set -eu
                touch {HOOK_MARKER}
            """),
            0,      # owner: root
            0,      # group: root
            0o700,
        ),
    }


"""
Verify that the Lego Quadlet is correctly installed and configured on a fresh VM boot.
"""
class TestLegoQuadlet(test_quadlet.TestQuadlet):
    expected_services = [
        {"name": "lego.target",     "state": "active", "exists": True},
        {"name": "lego.timer",      "state": "active", "exists": True},
        {"name": "lego-hooks.path", "state": "active", "exists": True},
    ]

    expected_files = [
        {"path": "/var/lib/quadlets/lego",           "type": "directory", "owner": "lego", "group": "itix-svc", "mode": 0o755},
        {"path": "/etc/quadlets/lego",               "type": "directory"},
        {"path": "/etc/quadlets/lego/deploy-hook.sh", "type": "file", "owner": "root", "mode": 0o755},
        {"path": "/etc/quadlets/lego/process-hooks.sh", "type": "file", "owner": "root", "mode": 0o755},
        {"path": "/etc/quadlets/lego/renew-hooks.d", "type": "directory"},
    ]

    expected_podman_images = [
        {"name": "docker.io/goacme/lego", "tag": "v5", "state": "present"},
    ]

    expected_main_service = "lego.target"
    expected_main_service_timeout = 600  # Allow time for image pull + ACME negotiation

    def get_serial(self, host) -> str:
        result = host.run(f"openssl x509 -in {CERT_PATH} -noout -serial")
        assert result.rc == 0, f"Failed to read certificate serial: {result.stderr}"
        return result.stdout.strip()

    def wait_for_hooks(self, host, timeout: int = 120) -> None:
        """Block until the hook marker exists and all .renewed files have been processed."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            marker = host.file(HOOK_MARKER).exists
            renewed = host.run(f"ls {CERT_DIR}/*.renewed 2>/dev/null | wc -l").stdout.strip()
            if marker and renewed == "0":
                return
            time.sleep(2)
        raise TimeoutError(
            f"Renewal hooks were not processed within {timeout}s:\n"
            + host.run("journalctl -u lego-hooks.service -u lego-hooks.path --no-pager -n 50").stdout
        )

    def run_lego(self, host) -> None:
        result = host.run("systemctl start lego.service")
        assert result.rc == 0, (
            f"lego.service failed: {result.stderr}\n"
            + host.run("journalctl -u lego.service --no-pager -n 50").stdout
        )

    # ------------------------------------------------------------------
    # Test 1 — TLS certificate retrieval
    # ------------------------------------------------------------------

    @pytest.mark.flaky(reruns=6, reruns_delay=10)
    def test_lego_certificate_obtained(self, fcos_host, top_level_domain, dns_server_ip):
        """lego.service must successfully fetch a TLS certificate from the Pebble ACME server."""
        state = self.wait_for_unit_done(fcos_host, "lego.service", timeout=600)
        if state == "failed":
            # The first attempt may fail if the DNS record of the VM was not
            # resolvable by Pebble when lego started: try again.
            prime_dns_cache(dns_server_ip, [f"lego.{top_level_domain}"])
            self.run_lego(fcos_host)

        for path in (CERT_PATH, KEY_PATH):
            f = fcos_host.file(path)
            assert f.is_file, f"{path} not found"
            assert f.user == "lego", f"{path} must be owned by lego, got {f.user}"
            assert f.mode == 0o600, f"{path} must not be world-readable: got {oct(f.mode)}"

        domain = f"lego.{top_level_domain}"
        result = fcos_host.run(f"openssl x509 -in {CERT_PATH} -noout -ext subjectAltName")
        assert result.rc == 0, f"openssl failed to parse certificate: {result.stderr}"
        assert f"DNS:{domain}" in result.stdout, (
            f"Expected {domain!r} in the certificate SAN:\n{result.stdout}"
        )

    # ------------------------------------------------------------------
    # Test 2 — Hooks are executed after the first issuance
    # ------------------------------------------------------------------

    def test_lego_hooks_executed_on_issuance(self, fcos_host):
        """lego-hooks.path must trigger process-hooks.sh, which runs renew-hooks.d/ and cleans up .renewed files."""
        self.wait_for_hooks(fcos_host)

    # ------------------------------------------------------------------
    # Test 3 — Lego is idempotent
    # ------------------------------------------------------------------

    def test_lego_skips_renewal(self, fcos_host):
        """A second run of lego.service must not renew a fresh certificate."""
        serial_before = self.get_serial(fcos_host)
        fcos_host.run(f"rm -f {HOOK_MARKER}")

        self.run_lego(fcos_host)

        assert self.get_serial(fcos_host) == serial_before, "The certificate has been renewed but should not"
        result = fcos_host.run("journalctl -u lego.service --no-pager -n 20")
        assert "Skip renewal" in result.stdout, f"Expected 'Skip renewal' in lego logs:\n{result.stdout}"
        time.sleep(5)
        assert not fcos_host.file(HOOK_MARKER).exists, "Hooks have been run but no certificate was renewed"

    # ------------------------------------------------------------------
    # Test 4 — Certificate renewal
    # ------------------------------------------------------------------

    @pytest.mark.flaky(reruns=3, reruns_delay=5)
    def test_lego_certificate_renewal(self, fcos_host, top_level_domain, dns_server_ip):
        """lego.service must obtain a new certificate when forced to (renew.days: -1) and run the hooks."""
        prime_dns_cache(dns_server_ip, [f"lego.{top_level_domain}"])
        serial_before = self.get_serial(fcos_host)
        fcos_host.run(f"rm -f {HOOK_MARKER}")

        # Force the renewal: a negative number of days always renews the certificate.
        result = fcos_host.run(
            f"cp -a {LEGO_CONFIG} {LEGO_CONFIG}.orig && "
            f"sed -i 's/disableRandomSleep: true/disableRandomSleep: true\\n      days: -1/' {LEGO_CONFIG}"
        )
        assert result.rc == 0, f"Failed to edit lego.yaml: {result.stderr}"
        try:
            self.run_lego(fcos_host)
        finally:
            fcos_host.run(f"mv {LEGO_CONFIG}.orig {LEGO_CONFIG}")

        assert self.get_serial(fcos_host) != serial_before, (
            f"Certificate serial did not change after renewal (still {serial_before})"
        )
        self.wait_for_hooks(fcos_host)

    # ------------------------------------------------------------------
    # Test 5 — Timer configuration
    # ------------------------------------------------------------------

    def test_lego_timer_configured(self, fcos_host):
        """lego.timer must be active and scheduled for daily execution."""
        result = fcos_host.run("systemctl show lego.timer --property=ActiveState,TimersCalendar,Unit")
        assert result.rc == 0
        assert "ActiveState=active" in result.stdout, f"lego.timer is not active:\n{result.stdout}"
        # OnCalendar=daily is normalized as "*-*-* 00:00:00"
        assert "OnCalendar=*-*-* 00:00:00" in result.stdout, (
            f"Expected a daily schedule in timer properties:\n{result.stdout}"
        )
        assert "Unit=lego.service" in result.stdout, f"lego.timer must start lego.service:\n{result.stdout}"

    # ------------------------------------------------------------------
    # Test 6 — Reboot survival (must run last)
    # ------------------------------------------------------------------

    def test_lego_survives_reboot(self, fcos_vm, fcos_host, test_ssh_key):
        """After a reboot, lego.target must be active and the certificate must be intact."""
        serial_before = self.get_serial(fcos_host)

        # Schedule the reboot so that the SSH command returns before the connection drops.
        result = fcos_host.run("systemd-run --on-active=3 systemctl reboot")
        assert result.rc == 0, f"Failed to schedule the reboot: {result.stderr}"
        time.sleep(15)  # let the reboot begin before we start polling SSH

        fcos_vm.wait_ssh(ssh_key=test_ssh_key, timeout=300)

        # The module-scoped fcos_host fixture is stale after reboot; create a fresh connection.
        new_host = testinfra.get_host(
            f"ssh://root@{fcos_vm.ip}",
            ssh_extra_args=(
                f"-i {test_ssh_key}"
                " -o StrictHostKeyChecking=no"
                " -o UserKnownHostsFile=/dev/null"
            ),
        )

        self.wait_for_service(new_host, "lego.target", timeout=300)
        self.check_expected_services(new_host, self.expected_services)

        # lego.service runs at each boot but must not renew a fresh certificate.
        state = self.wait_for_unit_done(new_host, "lego.service", timeout=300)
        assert state == "inactive", (
            f"lego.service ended in unexpected state: {state!r}\n"
            + new_host.run("journalctl -b -u lego.service --no-pager -n 50").stdout
        )
        result = new_host.run("systemctl show lego.service --property=Result")
        assert "Result=success" in result.stdout, f"lego.service did not succeed after reboot:\n{result.stdout}"

        assert self.get_serial(new_host) == serial_before, "Certificate changed after reboot"
