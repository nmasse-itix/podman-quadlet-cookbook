import ftplib
import io
import ssl
import subprocess
import textwrap
import time
import test_quadlet  # noqa: F401
import pytest
import testinfra

LEGO_CONFIG = "/etc/quadlets/lego/lego.yaml"
LEGO_CERT_PATH = "/var/lib/quadlets/lego/certificates/default.crt"
FTP_USER = "ftptest"
FTP_UID = 1500  # vsftpd.container rewrites the home of uids 1000-1999 to /data
FTP_PASSWORD = "S3cret-ftp-passw0rd"


def prime_dns_cache(dns_server_ip: str, names: list[str]) -> None:
    """Workaround for flaky ACME validations in the test environment.

    Pebble resolves the domains over TCP. When the libvirt dnsmasq has to forward the AAAA
    query of a test domain upstream over TCP, the query may time out. A UDP query puts the
    (negative) answer in the dnsmasq cache, so that the subsequent TCP query of Pebble succeeds.
    """
    for name in names:
        for qtype in ("A", "AAAA"):
            subprocess.run(["dig", "+time=2", "+tries=2", qtype, f"@{dns_server_ip}", name], capture_output=True)


class ReusedSessionFTP_TLS(ftplib.FTP_TLS):
    """FTP_TLS client that reuses the TLS session of the control connection on the data connections.

    vsftpd requires TLS session reuse by default (require_ssl_reuse=YES).
    """

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


@pytest.fixture(scope="module")
def dns_names() -> list[str]:
    """The FTP domain must be DNS-resolvable so Pebble can reach the VM on port 80 for HTTP-01 validation."""
    return ["ftp"]


@pytest.fixture(scope="module")
def ftp_domain(top_level_domain) -> str:
    return f"ftp.{top_level_domain}"


@pytest.fixture(scope="module")
def fcos_extra_files(pebble_acme_server, ftp_domain) -> dict:
    """Extra files to inject into the FCOS VM for vsftpd tests."""
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
                    email: test@{ftp_domain}
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
                      - {ftp_domain}
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
            0,
            0,
            0o644,
        ),
        # Drop-in to trust the Pebble CA.
        "/etc/containers/systemd/lego.container.d/pebble.conf": (
            textwrap.dedent("""\
                [Container]
                Environment=LEGO_CA_CERTIFICATES=/etc/lego/pebble.pem
            """),
            0,
            0,
            0o644,
        ),
        # vsftpd configuration: local users + TLS with the certificate provided by lego.
        "/etc/quadlets/vsftpd/vsftpd.conf.d/local.conf": (
            textwrap.dedent(f"""\
                pasv_address={ftp_domain}
                pasv_addr_resolve=YES
                local_enable=YES
                local_root=/data
                chroot_local_user=YES
                pam_service_name=vsftpd
                write_enable=YES
                allow_writeable_chroot=YES
                anonymous_enable=NO
                file_open_mode=0660
                ssl_enable=YES
                ssl_request_cert=NO
                ssl_tlsv1_2=NO
                ssl_tlsv1_3=YES
                rsa_cert_file=/etc/vsftpd/tls/default.crt
                rsa_private_key_file=/etc/vsftpd/tls/default.key
            """),
            0,
            0,
            0o644,
        ),
        # Storage shared through FTP.
        "/etc/tmpfiles.d/vsftpd-test.conf": (
            f"d /var/lib/vsftpd-test 0770 {FTP_UID} {FTP_UID} -\n",
            0,
            0,
            0o644,
        ),
        "/etc/containers/systemd/vsftpd.container.d/storage.conf": (
            textwrap.dedent("""\
                [Container]
                Volume=/var/lib/vsftpd-test:/data:z
            """),
            0,
            0,
            0o644,
        ),
    }


"""
Verify that vsftpd serves FTPS with a certificate obtained by lego.
"""
class TestVsftpdQuadlet(test_quadlet.TestQuadlet):
    # vsftpd needs the certificate obtained by lego, so the vsftpd services are
    # checked once lego has obtained it (see test_create_ftp_user).
    expected_services = [
        {"name": "lego.target",     "state": "active", "exists": True},
        {"name": "lego-hooks.path", "state": "active", "exists": True},
    ]

    expected_vsftpd_services = [
        {"name": "vsftpd.target",   "state": "active", "exists": True},
        {"name": "vsftpd.service",  "state": "active", "exists": True},
    ]

    expected_vsftpd_ports = [
        {"number": 21, "protocol": "tcp", "state": "open"},
    ]

    expected_files = [
        {"path": "/etc/quadlets/lego/renew-hooks.d/vsftpd.sh", "type": "file", "owner": "root", "mode": 0o755},
    ]

    # Certificates copied by vsftpd.service from the lego storage
    expected_tls_files = [
        {"path": "/run/quadlets/vsftpd/tls/default.crt", "type": "file", "owner": "root", "mode": 0o600},
        {"path": "/run/quadlets/vsftpd/tls/default.key", "type": "file", "owner": "root", "mode": 0o600},
    ]

    # The vsftpd image is built on first boot (see test_create_ftp_user).
    expected_vsftpd_images = [
        {"name": "localhost/vsftpd", "tag": "latest", "state": "present"},
    ]

    expected_main_service = "lego.target"
    expected_main_service_timeout = 600  # Image pull + ACME negotiation

    def ftps_connect(self, host_ip: str, ca_bundle: str) -> ReusedSessionFTP_TLS:
        """Open an authenticated FTPS session, trusting only the Pebble CA."""
        ctx = ssl.create_default_context(cadata=ca_bundle)
        # The VM is reached by IP: the hostname is checked separately against the certificate SAN.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_REQUIRED
        ftp = ReusedSessionFTP_TLS(context=ctx, timeout=30)
        ftp.connect(host_ip, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        ftp.prot_p()
        return ftp

    def served_certificate(self, host_ip: str, ca_bundle: str) -> dict:
        ftp = self.ftps_connect(host_ip, ca_bundle)
        try:
            return ftp.sock.getpeercert()
        finally:
            ftp.quit()

    def lego_serial(self, host) -> str:
        result = host.run(f"openssl x509 -in {LEGO_CERT_PATH} -noout -serial")
        assert result.rc == 0, f"Failed to read the lego certificate: {result.stderr}"
        return result.stdout.strip().removeprefix("serial=").upper()

    def wait_for_served_serial(self, host_ip: str, ca_bundle: str, serial: str, timeout: int = 180) -> None:
        deadline = time.monotonic() + timeout
        served = None
        while time.monotonic() < deadline:
            try:
                served = self.served_certificate(host_ip, ca_bundle)["serialNumber"].upper()
                if served == serial:
                    return
            except (OSError, ftplib.Error):
                pass  # vsftpd may be restarting
            time.sleep(5)
        raise TimeoutError(f"vsftpd serves certificate {served}, expected {serial}")

    # ------------------------------------------------------------------
    # Test 1 — Lego obtains the certificate
    # ------------------------------------------------------------------

    @pytest.mark.flaky(reruns=3, reruns_delay=10)
    def test_lego_certificate_obtained(self, fcos_host, dns_server_ip, ftp_domain):
        """lego.service must obtain the certificate from Pebble."""
        state = self.wait_for_unit_done(fcos_host, "lego.service", timeout=600)
        if state == "failed":
            # The first attempt may fail if the DNS record of the VM was not
            # resolvable by Pebble when lego started: try again.
            prime_dns_cache(dns_server_ip, [ftp_domain])
            result = fcos_host.run("systemctl start lego.service")
            assert result.rc == 0, (
                f"lego.service failed: {result.stderr}\n"
                + fcos_host.run("journalctl -u lego.service --no-pager -n 50").stdout
            )
        assert fcos_host.file(LEGO_CERT_PATH).is_file, f"{LEGO_CERT_PATH} not found"

    # ------------------------------------------------------------------
    # Test 2 — Create a local user
    # ------------------------------------------------------------------

    def test_create_ftp_user(self, fcos_host):
        """Create a local user and restart vsftpd so that it is part of its passwd cache."""
        result = fcos_host.run(
            f"id {FTP_USER} || useradd -u {FTP_UID} -U -M -d /var/lib/vsftpd-test {FTP_USER}"
        )
        assert result.rc == 0, f"useradd failed: {result.stderr}"
        result = fcos_host.run(f"echo '{FTP_USER}:{FTP_PASSWORD}' | chpasswd")
        assert result.rc == 0, f"chpasswd failed: {result.stderr}"
        # The vsftpd image build may take a while on first boot.
        state = self.wait_for_unit_done(fcos_host, "vsftpd-build.service", timeout=900)
        assert state == "inactive", (
            f"vsftpd-build.service ended in unexpected state: {state!r}\n"
            + fcos_host.run("journalctl -u vsftpd-build.service --no-pager -n 50").stdout
        )
        self.check_expected_podman_images(fcos_host, self.expected_vsftpd_images)
        result = fcos_host.run("systemctl restart vsftpd.service && systemctl start vsftpd.target")
        assert result.rc == 0, (
            f"Failed to restart vsftpd: {result.stderr}\n"
            + fcos_host.run("journalctl -u vsftpd.service --no-pager -n 50").stdout
        )
        self.check_expected_services(fcos_host, self.expected_vsftpd_services)
        self.check_expected_files(fcos_host, self.expected_tls_files)

    def test_vsftpd_ports(self, fcos_vm):
        """The FTP control port must be reachable."""
        self.check_expected_ports(fcos_vm, self.expected_vsftpd_ports)

    # ------------------------------------------------------------------
    # Test 3 — FTPS with the certificate obtained by lego
    # ------------------------------------------------------------------

    @pytest.mark.flaky(reruns=6, reruns_delay=10)
    def test_ftps_certificate(self, fcos_vm, fcos_host, pebble_acme_server, ftp_domain):
        """vsftpd must serve the certificate obtained by lego from Pebble."""
        cert = self.served_certificate(fcos_vm.ip, pebble_acme_server["ca_bundle"])
        san = [value for kind, value in cert.get("subjectAltName", ()) if kind == "DNS"]
        assert ftp_domain in san, f"Expected {ftp_domain!r} in the certificate SAN, got {san}"
        assert cert["serialNumber"].upper() == self.lego_serial(fcos_host), (
            "vsftpd does not serve the certificate obtained by lego"
        )

    def test_ftps_upload(self, fcos_vm, fcos_host, pebble_acme_server):
        """An authenticated user must be able to upload and list files over FTPS."""
        ftp = self.ftps_connect(fcos_vm.ip, pebble_acme_server["ca_bundle"])
        try:
            ftp.storbinary("STOR hello.txt", io.BytesIO(b"Hello, FTPS!\n"))
            assert "hello.txt" in ftp.nlst(), "Uploaded file not listed"
        finally:
            ftp.quit()
        assert fcos_host.file("/var/lib/vsftpd-test/hello.txt").content_string == "Hello, FTPS!\n"

    def test_plain_ftp_rejected(self, fcos_vm):
        """Local users must not be able to log in without TLS."""
        ftp = ftplib.FTP(timeout=30)
        ftp.connect(fcos_vm.ip, 21)
        try:
            with pytest.raises(ftplib.error_perm):
                ftp.login(FTP_USER, FTP_PASSWORD)
        finally:
            ftp.close()

    # ------------------------------------------------------------------
    # Test 4 — Renewal: the lego hook restarts vsftpd with the new certificate
    # ------------------------------------------------------------------

    @pytest.mark.flaky(reruns=3, reruns_delay=5)
    def test_certificate_renewal(self, fcos_vm, fcos_host, pebble_acme_server, dns_server_ip, ftp_domain):
        """When lego renews the certificate, vsftpd must serve the new one."""
        prime_dns_cache(dns_server_ip, [ftp_domain])
        serial_before = self.lego_serial(fcos_host)

        # Force the renewal: a negative number of days always renews the certificate.
        result = fcos_host.run(
            f"cp -a {LEGO_CONFIG} {LEGO_CONFIG}.orig && "
            f"sed -i 's/disableRandomSleep: true/disableRandomSleep: true\\n      days: -1/' {LEGO_CONFIG}"
        )
        assert result.rc == 0, f"Failed to edit lego.yaml: {result.stderr}"
        try:
            result = fcos_host.run("systemctl start lego.service")
            assert result.rc == 0, (
                f"lego.service failed: {result.stderr}\n"
                + fcos_host.run("journalctl -u lego.service --no-pager -n 50").stdout
            )
        finally:
            fcos_host.run(f"mv {LEGO_CONFIG}.orig {LEGO_CONFIG}")

        serial_after = self.lego_serial(fcos_host)
        assert serial_after != serial_before, "lego did not renew the certificate"
        self.wait_for_served_serial(fcos_vm.ip, pebble_acme_server["ca_bundle"], serial_after)

    # ------------------------------------------------------------------
    # Test 5 — Reboot survival (must run last)
    # ------------------------------------------------------------------

    def test_survives_reboot(self, fcos_vm, fcos_host, test_ssh_key, pebble_acme_server):
        """After a reboot, vsftpd must serve FTPS again (the tmpfs holding the certificates is repopulated)."""
        serial_before = self.lego_serial(fcos_host)

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

        self.wait_for_service(new_host, "vsftpd.target", timeout=300)
        self.check_expected_services(new_host, self.expected_services + self.expected_vsftpd_services)
        self.check_expected_files(new_host, self.expected_files + self.expected_tls_files)
        self.wait_for_served_serial(fcos_vm.ip, pebble_acme_server["ca_bundle"], serial_before)
