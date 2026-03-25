"""Pytest fixtures for the PostgreSQL cookbook end-to-end tests.

Prerequisites:
  - Must run as root (KVM/libvirt access).
  - The Fedora CoreOS base QCOW2 image must be present at
    /var/lib/libvirt/images/library/fedora-coreos.qcow2.
    Run ``coreos-installer download -p qemu -f qcow2.xz -d
    -C /var/lib/libvirt/images/library/`` to fetch it.
  - fcos.ign for the postgresql cookbook is built on demand by
    ``make -C postgresql butane`` if it is missing.  This requires
    local.bu (SSH keys, user setup) to be present at the repository root.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import testinfra

REPO_ROOT = Path(__file__).parent.parent.parent
POSTGRESQL_DIR = REPO_ROOT / "postgresql"

# Add directories to the path so we can import local helpers and shared vm.py.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO_ROOT / "tests"))
from vm import FCOSVirtualMachine, build_test_ignition, ensure_fcos_ign  # noqa: E402

from helpers import (
    PG_DB,
    PG_MAJOR_DEFAULT,
    PG_MAJOR_UPGRADE_FROM,
    PG_MAJOR_UPGRADE_TO,
    PG_PASSWORD,
    PG_USER,
    run_sql,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_config_env(pg_major: str) -> dict[str, str]:
    """Return the full default config.env content as a dict for the given PG major."""
    return {
        "PG_MAJOR": pg_major,
        "POSTGRES_USER": PG_USER,
        "POSTGRES_PASSWORD": PG_PASSWORD,
        "POSTGRES_DB": PG_DB,
        "POSTGRES_HOST_AUTH_METHOD": "scram-sha-256",
        "POSTGRES_INITDB_ARGS": "--auth-host=scram-sha-256",
        "POSTGRES_ARGS": "-h 127.0.0.1",
        "PGPORT": "5432",
        "POSTGRES_BACKUP_RETENTION": "7",
    }


# ---------------------------------------------------------------------------
# Shared fixtures (module-scoped → one VM per test module)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def virtiofs_dir() -> Path:
    """Unique VirtioFS host directory for the default test VM."""
    d = Path("/srv") / f"fcos-test-postgresql-{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    if d.exists():
        shutil.rmtree(d)


@pytest.fixture(scope="module")
def postgresql_vm(
    test_ssh_key: Path,
    test_ssh_pubkey: str,
    virtiofs_dir: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> FCOSVirtualMachine:
    """Running CoreOS VM with PostgreSQL installed at the default PG version.

    The VM is created once per test module and destroyed in teardown.
    All tests in the same module share this VM instance.
    """
    fcos_ign = ensure_fcos_ign(POSTGRESQL_DIR)
    test_ign = tmp_path_factory.mktemp("ign") / "fcos-test.ign"
    build_test_ignition(
        base_ignition=fcos_ign,
        ssh_pubkey=test_ssh_pubkey,
        output=test_ign,
    )

    vm = FCOSVirtualMachine(
        name=f"postgresql-{os.getpid()}",
        ignition_file=test_ign,
        virtiofs_dir=virtiofs_dir,
    )
    vm.create()
    vm.wait_ssh(ssh_key=test_ssh_key, timeout=300)
    vm.wait_for_service("postgresql.target", ssh_key=test_ssh_key, timeout=300)

    yield vm

    vm.destroy()


@pytest.fixture(scope="module")
def pg_host(postgresql_vm: FCOSVirtualMachine, test_ssh_key: Path):
    """testinfra SSH host connected to the default PostgreSQL VM."""
    return testinfra.get_host(
        f"ssh://root@{postgresql_vm.ip}",
        ssh_extra_args=(
            f"-i {test_ssh_key}"
            " -o StrictHostKeyChecking=no"
            " -o UserKnownHostsFile=/dev/null"
        ),
    )


@pytest.fixture(scope="module")
def upgrade_virtiofs_dir() -> Path:
    """Unique VirtioFS host directory for the upgrade test VM."""
    d = Path("/srv") / f"fcos-test-pg-upgrade-{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    if d.exists():
        shutil.rmtree(d)


@pytest.fixture(scope="module")
def upgrade_vm(
    test_ssh_key: Path,
    test_ssh_pubkey: str,
    upgrade_virtiofs_dir: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> FCOSVirtualMachine:
    """Running CoreOS VM with PostgreSQL installed at PG_MAJOR_UPGRADE_FROM.

    Used exclusively by test_upgrade.py to verify the major version upgrade path.
    The config.env is overridden via the ignition overlay so the VM boots
    directly with PG_MAJOR_UPGRADE_FROM, regardless of the cookbook's default.
    """
    fcos_ign = ensure_fcos_ign(POSTGRESQL_DIR)
    test_ign = tmp_path_factory.mktemp("ign-upgrade") / "fcos-upgrade.ign"
    build_test_ignition(
        base_ignition=fcos_ign,
        ssh_pubkey=test_ssh_pubkey,
        output=test_ign,
        config_env_overrides=_default_config_env(PG_MAJOR_UPGRADE_FROM),
    )

    vm = FCOSVirtualMachine(
        name=f"pg-upgrade-{os.getpid()}",
        ignition_file=test_ign,
        virtiofs_dir=upgrade_virtiofs_dir,
    )
    vm.create()
    vm.wait_ssh(ssh_key=test_ssh_key, timeout=300)
    vm.wait_for_service("postgresql.target", ssh_key=test_ssh_key, timeout=300)

    yield vm

    vm.destroy()
