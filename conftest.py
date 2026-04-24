"""Pytest fixtures for the Podman Quadlets cookbooks.

Prerequisites:
  - Must run as root (KVM/libvirt access).
  - The Fedora CoreOS base QCOW2 image must be present at /var/lib/libvirt/images/library/fedora-coreos.qcow2.
    Run ``coreos-installer download -p qemu -f qcow2.xz -d -C /var/lib/libvirt/images/library/`` to fetch it.
  - fcos-test.ign for the cookbook is built on demand by ``make butane`` if it is missing.
  - The rootful Podman socket must be enabled (systemctl enable --now podman.socket) for the
    pebble_acme_server fixture to start a Pebble ACME container via Testcontainers.
"""

import json
import os
import re
import shutil
import socket as _socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path
import urllib.request
import ssl

import pytest
import testinfra

from fcos_vm import FCOSVirtualMachine, ensure_fcos_ign  # noqa: E402
from dns_server import DNSServer  # noqa: E402

# Persistent directory used when --keep is active.
_KEEP_VM_CACHE_DIR = Path.home() / ".cache" / "pytest"

@pytest.fixture(scope="session")
def libvirt_network() -> str:
    """The libvirt network name to use."""
    return "default"

@pytest.fixture(scope="session")
def libvirt_network_if(libvirt_network: str) -> str:
    """The libvirt network interface to use."""
    result = subprocess.run(
        ["virsh", "net-info", libvirt_network],
        capture_output=True, text=True, check=True,
    )
    match = re.search(r"Bridge:\s+(\S+)", result.stdout)
    if match:
        return match.group(1)
    raise RuntimeError(f"Could not find interface for libvirt network '{libvirt_network}'")

@pytest.fixture(scope="session")
def pebble_server_ip(libvirt_network_if: str) -> str:
    """IP Address of the Pebble ACME server."""
    return _get_libvirt_bridge_ip(libvirt_network_if)

@pytest.fixture(scope="session")
def top_level_domain() -> str:
    """Top-level domain for the test environment."""
    return "pytest.example.test"

@pytest.fixture(scope="session")
def dns_server_ip(libvirt_network_if: str) -> str:
    """IP Address of the DNS server."""
    return _get_libvirt_bridge_ip(libvirt_network_if)

def _get_libvirt_bridge_ip(libvirt_network_if: str) -> str:
    """Return the IP of the host running pytest, as seen from the test VMs."""
    result = subprocess.run(
        ["ip", "-4", "-j", "addr", "show", "scope", "global", "dev", libvirt_network_if],
        capture_output=True, text=True, check=True,
    )
    ip_info = json.loads(result.stdout)
    if ip_info and "addr_info" in ip_info[0] and ip_info[0]["addr_info"]:
        return ip_info[0]["addr_info"][0]["local"]
    raise RuntimeError(f"Could not find IP address for libvirt network interface '{libvirt_network_if}'")

def _wait_for_port(host: str, port: int, timeout: int = 30) -> None:
    """Wait for a TCP port to be open on the given host, or raise after timeout."""
    timeout = 30
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with _socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"Port {host}:{port} not available after {timeout}s")

# You can pass --keep on the command line to keep the test VM alive after the test run and reuse it on the next run.
# Speeds up iteration: the VM is created once and never destroyed. The SSH key is stored persistently in ~/.cache/pytest.
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--keep",
        action="store_true",
        default=False,
        help=(
            "Keep the test VM alive after the test run and reuse it on the next run. "
            "Speeds up iteration: the VM is created once and never destroyed. "
            "The SSH key is stored persistently in "
            f"{_KEEP_VM_CACHE_DIR}."
        ),
    )

@pytest.fixture(scope="session")
def keep(request: pytest.FixtureRequest) -> bool:
    """True when --keep was passed on the command line."""
    return request.config.getoption("--keep")

@pytest.fixture(scope="session")
def pebble_acme_server(tmp_path_factory: pytest.TempPathFactory, pebble_server_ip: str, dns_server_ip: str, keep: bool) -> dict:
    """Session-scoped Pebble ACME test server running in a Podman container.

    Pebble is configured to validate HTTP-01 challenges on standard ports
    (80/443) and binds to all host interfaces via host networking so it is
    reachable from the libvirt test VMs.

    The rootful Podman socket must be enabled before running the tests:
        systemctl enable --now podman.socket

    Yields a dict with:
      - directory_url : ACME directory URL (https://<bridge_ip>:14000/dir)
      - ca_cert       : Pebble root CA certificate (PEM string), used to
                        authenticate Pebble's own TLS endpoint.
    """
    from testcontainers.core.container import DockerContainer

    # Point Testcontainers at the rootful Podman socket and disable Ryuk
    # (Ryuk does not work reliably with Podman).
    os.environ.setdefault("DOCKER_HOST", "unix:///run/podman/podman.sock")
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

    if keep:
        pebble_dir = Path("/srv/pebble")
        pebble_dir.mkdir(parents=True, exist_ok=True)
    else:
        pebble_dir = tmp_path_factory.mktemp("pebble")

    etc_dir = pebble_dir / "etc"
    etc_dir.mkdir(exist_ok=True)
    var_dir = pebble_dir / "var"
    var_dir.mkdir(exist_ok=True)
    ca_cert_path = var_dir / "ca.crt"
    ca_key_path = var_dir / "ca.key"
    server_key_path = var_dir / "server.key"
    server_cert_path = var_dir / "server.crt"

    # Generate a self-signed certificate for Pebble to use.
    # The certificate's CN must match the host IP visible from the VM for TLS to work.
    # The keys and certificates are reused across runs when --keep is set because those artefacts
    # are injected into the VM and must remain consistent for the VM to be reusable.
    if not (ca_cert_path.exists() and ca_key_path.exists()):
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(ca_key_path), "-out", str(ca_cert_path), "-days", "3650", "-noenc",
            "-subj", "/CN=Pebble CA", "-addext", "basicConstraints=critical,CA:TRUE"], check=True, capture_output=True)

    if not (var_dir / "server.csr").exists():
        subprocess.run(["openssl", "req", "-newkey", "rsa:2048",
            "-keyout", str(server_key_path), "-out", str(var_dir / "server.csr"), "-noenc",
            "-subj", "/CN=localhost"], check=True, capture_output=True)
    
    if not server_cert_path.exists():
        (pebble_dir / "srv_ext.txt").write_text(f"basicConstraints=CA:FALSE\nsubjectAltName=IP:127.0.0.1,IP:{pebble_server_ip},DNS:localhost\n")
        subprocess.run(["openssl", "x509", "-req",
            "-in", str(var_dir / "server.csr"), "-CA", str(ca_cert_path), "-CAkey", str(ca_key_path), "-CAcreateserial",
            "-out", str(server_cert_path), "-days", "365", "-extfile", str(pebble_dir / "srv_ext.txt")], check=True, capture_output=True)

    # Write the Pebble configuration with standard challenge ports (80 / 443).
    config_file = etc_dir / "pebble-config.json"
    config_file.write_text(json.dumps({
        "pebble": {
            "listenAddress": "0.0.0.0:14000",
            "managementListenAddress": "0.0.0.0:15000",
            "certificate": "/test/certs/server.crt",
            "privateKey": "/test/certs/server.key",
            # Use standard ports to validate HTTP-01 & TLS-ALPN-01 challenges.
            "httpPort": 80,
            "httpsPort": 443,
            "externalAccountBindingRequired": False,
            "domainBlocklist": [],
        }
    }))

    container = (
        DockerContainer("ghcr.io/letsencrypt/pebble:latest")
        .with_name("pebble-acme-server")
        .with_env("PEBBLE_VA_NOSLEEP", "1")
        .with_env("PEBBLE_WFE_NONCEREJECT", "0")
        .with_command(f"-config /test/config/pebble-config.json -dnsserver {dns_server_ip}:53")
        .with_volume_mapping(str(etc_dir), "/test/config", "ro,z")
        .with_volume_mapping(str(var_dir), "/test/certs", "ro,z")
        .with_kwargs(
            network_mode="host",
        )
    )

    with container:
        _wait_for_port(pebble_server_ip, 14000)

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        certs = {}
        for name, path in [("root", "roots/0"), ("intermediate", "intermediates/0")]:
            url = f"https://{pebble_server_ip}:15000/{path}"
            with urllib.request.urlopen(url, context=ctx) as resp:
                certs[name] = resp.read().decode()
        
        data = {
            # The directory URL is how ACME clients discover the available endpoints and must be provided to the tests.
            "directory_url": f"https://{pebble_server_ip}:14000/dir",
            # The CA certificate is needed by the tests to authenticate Pebble's TLS endpoint.
            "ca_cert": ca_cert_path.read_text(),
            # The CA bundle to trust the generated certificates.
            "ca_bundle": certs["intermediate"] + certs["root"],
        }

        yield data # <-- tests run here with access to the Pebble ACME server

@pytest.fixture(scope="session")
def dns_server(libvirt_network: str, top_level_domain: str, keep: bool) -> DNSServer:
    """Session-scoped DNS server manager for the libvirt network."""
    srv = DNSServer(network=libvirt_network, persistent=keep)
    srv.set_domain(top_level_domain)

    yield srv # <-- tests run here with access to the DNS server manager
    
    srv.cleanup()

@pytest.fixture(scope="module")
def fcos_extra_files(request: pytest.FixtureRequest) -> dict:
    """Extra files to inject into the FCOS VM image.

    Defaults to the ``PYTEST_FCOS_EXTRA_FILES`` module-level dict (backward
    compatible with existing test modules).  Override this fixture in a test
    module to provide dynamic content whose values depend on other fixtures
    (e.g. files that embed the Pebble ACME server URL or CA certificate).
    """
    return getattr(request.module, "PYTEST_FCOS_EXTRA_FILES", {})

@pytest.fixture(scope="session")
def test_ssh_key(
    keep: bool,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """SSH key pair for VM access.

    When --keep is set the key is stored persistently so that subsequent
    runs can re-use the same VM without re-injecting a new key.
    """
    if keep:
        key_dir = _KEEP_VM_CACHE_DIR
        key_dir.mkdir(parents=True, exist_ok=True)
        key_path = key_dir / "id_ed25519"
        if not key_path.exists():
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(key_path)],
                check=True,
                capture_output=True,
            )
        return key_path

    key_dir = tmp_path_factory.mktemp("ssh-key")
    key_path = key_dir / "id_ed25519"
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(key_path)],
        check=True,
        capture_output=True,
    )
    return key_path


@pytest.fixture(scope="session")
def test_ssh_pubkey(test_ssh_key: Path) -> str:
    """Public key string corresponding to test_ssh_key."""
    return test_ssh_key.with_suffix(".pub").read_text().strip()

# The virtiofs is where important and persistent data are stored.
# We keep it for the entire test session.
@pytest.fixture(scope="package")
def virtiofs_dirs(request, keep: bool) -> list[tuple[Path, str]]:
    """VirtioFS host directories for the default test VM.

    With --keep the directories are persistent so the VM can be reused across
    test runs.  Without it unique per-process paths are used and cleaned up
    on teardown.
    """
    cookbook_dir = Path(request.path).parent.parent
    if keep:
        d = Path("/srv") / f"fcos-test-{cookbook_dir.name}-dev"
    else:
        d = Path("/srv") / f"fcos-test-{cookbook_dir.name}-{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    
    yield [(d, "data",)] # <-- tests run here with access to the virtiofs directories

    if not keep and d.exists():
        shutil.rmtree(d)

# However, the VM itself is recreated for each test module to ensure a clean state.
@pytest.fixture(scope="module")
def fcos_host(fcos_vm: FCOSVirtualMachine, test_ssh_key: Path):
    """testinfra SSH host connected to the default FCOS VM."""
    return testinfra.get_host(
        f"ssh://root@{fcos_vm.ip}",
        ssh_extra_args=(
            f"-i {test_ssh_key}"
            " -o StrictHostKeyChecking=no"
            " -o UserKnownHostsFile=/dev/null"
        ),
    )

# Default VM configuration (memory in MB, vCPUs, root disk size in GB, /var disk size in GB).
@pytest.fixture(scope="package")
def fcos_vm_config() -> tuple[int, int, int, int]:
    """Default VM configuration (memory in MB, vCPUs, root disk size in GB, /var disk size in GB)."""
    return (4096, 2, 50, 100) # (memory in MB, vCPUs, disk size for / and /var in GB)

@pytest.fixture(scope="module")
def dns_names() -> list[str]:
    """List of DNS names to be resolved by the VM (e.g. for ACME challenges)."""
    return [ ]

# Test VM are kept for the duration of a test module, backed with a persistent Virtiofs directory.
@pytest.fixture(scope="module")
def fcos_vm(
    request,                                    # Fixture that provides information about the requesting test function, class or module.
    keep: bool,                              # Fixture passed from command line option --keep to determine whether to keep the VM after tests for debugging purposes.
    fcos_vm_config: tuple[int, int, int, int],  # Fixture that provides the VM configuration (memory in MB, vCPUs, root disk size in GB, /var disk size in GB).
    test_ssh_key: Path,                         # Fixture that provides the path to the SSH private key to connect to the VM.
    test_ssh_pubkey: str,                       # Fixture that provides the content of the SSH public key to inject into the VM for SSH access.
    virtiofs_dirs: list[tuple[Path, str]],      # Fixture that provides a list of tuples containing host directories and their corresponding target directories in the VM to be exposed via VirtioFS.
    tmp_path_factory: pytest.TempPathFactory,   # Fixture that provides a factory for creating temporary directories.
    fcos_extra_files: dict,                     # Fixture that provides extra files to inject into the FCOS VM image (overridable per module).
    dns_server: DNSServer,                      # Fixture that provides a DNS server manager to configure DNS entries for the test VMs.
    dns_names: list[str],                       # Fixture that provides a list of DNS names to be resolved by the VM (e.g. for ACME challenges)
) -> FCOSVirtualMachine:
    """Running CoreOS VM with Quadlets installed.

    With --keep the VM is reused across runs: it is created only if it
    does not already exist and is never destroyed on teardown.
    """
    module_name = request.module.__name__.split(".")[-1].replace("test_", "").replace("_", "-")
    cookbook_dir = Path(request.path).parent.parent
    pg_major = getattr(request.module, "PG_MAJOR_DEFAULT", 0)
    vm = FCOSVirtualMachine(
        cookbook_name=cookbook_dir.name,
        instance_name=module_name,
        keep=keep,
        virtiofs_dirs=virtiofs_dirs,
        vm_config = fcos_vm_config,
    )

    if not (keep and vm.exists()):
        fcos_ign = ensure_fcos_ign(cookbook_dir)
        vm.ignition.ignition_files.append(fcos_ign)
        vm.ignition.extra_files.update(fcos_extra_files)
        vm.ignition.ssh_key = test_ssh_pubkey
        vm.create()
        vm.wait_ip()
        dns_server.add_host(vm.ip, [ vm.vm_name ] + dns_names)

    vm.wait_ssh(ssh_key=test_ssh_key, timeout=300)

    yield vm # <-- tests run here with access to the VM instance

    if not keep:
        vm.destroy()
        dns_server.remove_host(vm.ip)
