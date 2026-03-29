"""Test that a fresh PostgreSQL installation is secure.

These tests run against a brand-new VM booted from the cookbook's default
ignition (PG_MAJOR=14, example credentials).  They verify:
  - The PostgreSQL port is NOT exposed to the network.
  - The PostgreSQL backup directory has the correct ownership and permissions.
"""

from pathlib import Path
import socket

# ---------------------------------------------------------------------------
# Network / socket
# ---------------------------------------------------------------------------

def test_postgresql_port_listening(pg_host):
    """PostgreSQL must be listening on 127.0.0.1:5432 (POSTGRES_ARGS=-h 127.0.0.1)."""
    assert pg_host.socket("tcp://127.0.0.1:5432").is_listening


def test_postgresql_port_not_exposed(postgresql_vm):
    """PostgreSQL must NOT be exposed to the network."""

    # Positive control: port 22 (SSH) must be reachable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    assert s.connect_ex((postgresql_vm.ip, 22)) == 0, (
        f"Port 22 is NOT reachable from the host on {postgresql_vm.ip}!"
    )
    s.close()

    # Negative control: port 23 must NOT be reachable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    assert s.connect_ex((postgresql_vm.ip, 23)) != 0, (
        f"Port 23 is reachable from the host on {postgresql_vm.ip}!"
    )
    s.close()

    # The real test: port 5432 must NOT be reachable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    assert s.connect_ex((postgresql_vm.ip, 5432)) != 0, (
        f"Port 5432 is reachable from the host on {postgresql_vm.ip}!"
    )
    s.close()

# ---------------------------------------------------------------------------
# VirtioFS permissions (verified from the host — no SSH required)
# ---------------------------------------------------------------------------

def test_backup_directory_exists_in_virtiofs(virtiofs_dir: Path):
    """The postgresql/backup sub-directory must exist in the VirtioFS share."""
    backup_root = virtiofs_dir / "postgresql" / "backup"
    assert backup_root.exists(), f"Backup directory not found on host: {backup_root}"
    # mode 0700 — world and group bits must be 0
    assert backup_root.stat().st_mode & 0o077 == 0
    assert backup_root.stat().st_uid == 10004, f"Backup directory must be owned by postgres (uid 10004), but got {backup_root.stat().st_uid}"
    assert backup_root.stat().st_gid == 10000, f"Backup directory must be owned by postgres (gid 10000), but got {backup_root.stat().st_gid}"
