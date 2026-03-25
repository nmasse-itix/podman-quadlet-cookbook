"""Test PostgreSQL backup creation and VirtioFS storage.

These tests verify that:
  - The backup oneshot service can be triggered manually and runs to completion.
  - The expected backup artefacts land in the VirtioFS share (accessible from
    the test runner's host filesystem without SSH).
  - The backup retention policy removes stale backups.

Note: tests within a module share a single VM (module-scoped fixture), so
the order of test execution matters here: the backup files checked in later
tests are created by the earlier trigger test.
"""

import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Trigger and completion
# ---------------------------------------------------------------------------

def test_create_database_and_table(postgresql_vm, test_ssh_key):
    """Create a test database and table with some data to ensure the backup has
    something to capture."""
    postgresql_vm.ssh_run(
        "podman exec postgresql-server psql -U postgres -c \"CREATE DATABASE test;\"",
        test_ssh_key,
    )
    postgresql_vm.ssh_run(
        "podman exec postgresql-server psql -U postgres -d test -c \"CREATE TABLE witness (id SERIAL PRIMARY KEY, version VARCHAR); INSERT INTO witness (version) SELECT version();\"",
        test_ssh_key,
    )

def test_trigger_backup(postgresql_vm, test_ssh_key):
    """Starting postgresql-backup.service must succeed (no immediate error)."""
    postgresql_vm.ssh_run(
        "systemctl start postgresql-backup.service",
        test_ssh_key,
    )


def test_backup_completes_successfully(postgresql_vm, test_ssh_key):
    """postgresql-backup.service must finish in ``inactive`` state (not ``failed``)."""
    state = postgresql_vm.wait_for_unit_done(
        "postgresql-backup.service", test_ssh_key, timeout=120
    )
    assert state == "inactive", (
        f"Backup service ended in unexpected state {state!r}. "
        "Run: systemctl status postgresql-backup.service --no-pager"
    )


# ---------------------------------------------------------------------------
# VirtioFS artefacts (verified from the host — no SSH required)
# ---------------------------------------------------------------------------


def test_backup_directory_exists_in_virtiofs(virtiofs_dir: Path):
    """The postgresql/backup sub-directory must exist in the VirtioFS share."""
    backup_root = virtiofs_dir / "postgresql" / "backup"
    assert backup_root.is_dir(), f"Backup directory not found on host: {backup_root}"


def test_at_least_one_backup_present(virtiofs_dir: Path):
    """At least one timestamped backup sub-directory must exist."""
    backup_root = virtiofs_dir / "postgresql" / "backup"
    backups = sorted(backup_root.iterdir())
    assert backups, f"No backup sub-directories found under {backup_root}"


def test_backup_manifest_present(virtiofs_dir: Path):
    """The latest backup must contain a ``backup_manifest`` file (pg_basebackup)."""
    backup_root = virtiofs_dir / "postgresql" / "backup"
    latest = sorted(backup_root.iterdir())[-1]
    assert (latest / "backup_manifest").exists(), (
        f"backup_manifest missing in {latest}"
    )


def test_backup_base_tar_present(virtiofs_dir: Path):
    """The latest backup must contain a ``base.tar`` cluster archive."""
    backup_root = virtiofs_dir / "postgresql" / "backup"
    latest = sorted(backup_root.iterdir())[-1]
    assert (latest / "base.tar").exists(), f"base.tar missing in {latest}"


def test_database_dump_present(virtiofs_dir: Path):
    """At least one ``dump-test.sql.gz`` file must exist alongside the cluster backup."""
    backup_root = virtiofs_dir / "postgresql" / "backup"
    latest = sorted(backup_root.iterdir())[-1]
    dumps = list(latest.glob("dump-test.sql.gz"))
    assert dumps, f"No dump-test.sql.gz files found in {latest}"

# ---------------------------------------------------------------------------
# Retention policy
# ---------------------------------------------------------------------------


def test_backup_retention_enforced(postgresql_vm, test_ssh_key, virtiofs_dir: Path):
    """After triggering several extra backups the count must stay within the
    configured retention limit (POSTGRES_BACKUP_RETENTION=7)."""
    retention = 7

    # Trigger ten additional backups so the rotation code has something to do.
    for _ in range(10):
        postgresql_vm.ssh_run(
            "systemctl start postgresql-backup.service", test_ssh_key
        )
        state = postgresql_vm.wait_for_unit_done(
            "postgresql-backup.service", test_ssh_key, timeout=120
        )
        assert state == "inactive"
        time.sleep(1)  # ensure distinct timestamp directories

    backup_root = virtiofs_dir / "postgresql" / "backup"
    count = len(list(backup_root.iterdir()))
    assert count <= retention, (
        f"Retention policy failed: {count} backups present, expected ≤ {retention}"
    )
