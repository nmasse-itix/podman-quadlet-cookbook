"""Pytest fixtures for the PostgreSQL cookbook end-to-end tests.

Prerequisites:
  - Must run as root (KVM/libvirt access).
  - The Fedora CoreOS base QCOW2 image must be present at /var/lib/libvirt/images/library/fedora-coreos.qcow2.
    Run ``coreos-installer download -p qemu -f qcow2.xz -d -C /var/lib/libvirt/images/library/`` to fetch it.
  - fcos.ign for the postgresql cookbook is built on demand by ``make -C postgresql butane`` if it is missing.
"""

import shutil
import sys

import pytest
import testinfra

from pathlib import Path
THIS_COOKBOOK_DIR = Path(__file__).parent.parent
COOKBOOKS_DIR = THIS_COOKBOOK_DIR.parent
TOP_LEVEL_DIR = COOKBOOKS_DIR.parent
THIS_COOKBOOK_NAME = THIS_COOKBOOK_DIR.name

# Add directories to the path so we can import local helpers and shared vm.py.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(TOP_LEVEL_DIR / "tests"))
from fcos_vm import FCOSVirtualMachine, ensure_fcos_ign  # noqa: E402

# The virtiofs is where important and persistent data are stored.
# We keep it for the entire test session.
@pytest.fixture(scope="session")
def virtiofs_dirs(keep_vm: bool) -> list[tuple[Path, str]]:
    """VirtioFS host directories for the default test VM.

    With --keep-vm the directories are persistent so the VM can be reused across
    test runs.  Without it unique per-process paths are used and cleaned up
    on teardown.
    """
    if keep_vm:
        d = Path("/srv") / f"fcos-test-{THIS_COOKBOOK_NAME}-dev"
    else:
        d = Path("/srv") / f"fcos-test-{THIS_COOKBOOK_NAME}-{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    
    yield [(d, "data",)] # <-- tests run here with access to the virtiofs directories

    if not keep_vm and d.exists():
        shutil.rmtree(d)

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
