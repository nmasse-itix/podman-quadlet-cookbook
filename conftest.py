"""Pytest fixtures for the Podman Quadlets cookbooks.

Prerequisites:
  - Must run as root (KVM/libvirt access).
  - The Fedora CoreOS base QCOW2 image must be present at /var/lib/libvirt/images/library/fedora-coreos.qcow2.
    Run ``coreos-installer download -p qemu -f qcow2.xz -d -C /var/lib/libvirt/images/library/`` to fetch it.
  - fcos-test.ign for the cookbook is built on demand by ``make butane`` if it is missing.
"""

import subprocess
from pathlib import Path
import shutil
import os
import sys
import pytest
import testinfra
import textwrap

from fcos_vm import FCOSVirtualMachine, ensure_fcos_ign  # noqa: E402

# Persistent directory used when --keep-vm is active.
_KEEP_VM_CACHE_DIR = Path.home() / ".cache" / "pytest"

# You can pass --keep-vm on the command line to keep the test VM alive after the test run and reuse it on the next run.
# Speeds up iteration: the VM is created once and never destroyed. The SSH key is stored persistently in ~/.cache/pytest.
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--keep-vm",
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
def keep_vm(request: pytest.FixtureRequest) -> bool:
    """True when --keep-vm was passed on the command line."""
    return request.config.getoption("--keep-vm")


@pytest.fixture(scope="session")
def test_ssh_key(
    keep_vm: bool,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """SSH key pair for VM access.

    When --keep-vm is set the key is stored persistently so that subsequent
    runs can re-use the same VM without re-injecting a new key.
    """
    if keep_vm:
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
def virtiofs_dirs(request, keep_vm: bool) -> list[tuple[Path, str]]:
    """VirtioFS host directories for the default test VM.

    With --keep-vm the directories are persistent so the VM can be reused across
    test runs.  Without it unique per-process paths are used and cleaned up
    on teardown.
    """
    cookbook_dir = Path(request.path).parent.parent
    if keep_vm:
        d = Path("/srv") / f"fcos-test-{cookbook_dir.name}-dev"
    else:
        d = Path("/srv") / f"fcos-test-{cookbook_dir.name}-{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    
    yield [(d, "data",)] # <-- tests run here with access to the virtiofs directories

    if not keep_vm and d.exists():
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

# PostgreSQL VM are kept for the duration of a test module, backed with a persistent Virtiofs directory.
@pytest.fixture(scope="module")
def fcos_vm(
    request,                                    # Fixture that provides information about the requesting test function, class or module.
    keep_vm: bool,                              # Fixture passed from command line option --keep-vm to determine whether to keep the VM after tests for debugging purposes.
    fcos_vm_config: tuple[int, int, int, int],  # Fixture that provides the VM configuration (memory in MB, vCPUs, root disk size in GB, /var disk size in GB).
    test_ssh_key: Path,                         # Fixture that provides the path to the SSH private key to connect to the VM.
    test_ssh_pubkey: str,                       # Fixture that provides the content of the SSH public key to inject into the VM for SSH access.
    virtiofs_dirs: list[tuple[Path, str]],      # Fixture that provides a list of tuples containing host directories and their corresponding target directories in the VM to be exposed via VirtioFS.
    tmp_path_factory: pytest.TempPathFactory,   # Fixture that provides a factory for creating temporary directories.
) -> FCOSVirtualMachine:
    """Running CoreOS VM with Quadlets installed.

    With --keep-vm the VM is reused across runs: it is created only if it
    does not already exist and is never destroyed on teardown.
    """
    module_name = request.module.__name__.split(".")[-1].replace("test_", "").replace("_", "-")
    cookbook_dir = Path(request.path).parent.parent
    pg_major = getattr(request.module, "PG_MAJOR_DEFAULT", 0)
    vm = FCOSVirtualMachine(
        cookbook_name=cookbook_dir.name,
        instance_name=module_name,
        keep=keep_vm,
        virtiofs_dirs=virtiofs_dirs,
        vm_config = fcos_vm_config,
    )

    if not (keep_vm and vm.exists()):
        fcos_ign = ensure_fcos_ign(cookbook_dir)
        vm.ignition.ignition_files.append(fcos_ign)
        vm.ignition.extra_files.update(getattr(request.module, "PYTEST_FCOS_EXTRA_FILES", {}))
        vm.ignition.ssh_key = test_ssh_pubkey
        vm.create()

    vm.wait_ssh(ssh_key=test_ssh_key, timeout=300)

    yield vm # <-- tests run here with access to the VM instance

    if not keep_vm:
        vm.destroy()

