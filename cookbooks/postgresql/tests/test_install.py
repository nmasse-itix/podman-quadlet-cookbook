"""Test that a fresh PostgreSQL installation is healthy.

These tests run against a brand-new VM booted from the cookbook's default
ignition (PG_MAJOR=14, example credentials).  They verify:
  - All expected systemd units are in the correct state.
  - The PostgreSQL server is listening and accepts queries.
  - VirtioFS is mounted and the expected directories exist.
"""

from pathlib import Path

from helpers import PG_MAJOR_DEFAULT, run_sql


# ---------------------------------------------------------------------------
# Systemd unit state
# ---------------------------------------------------------------------------


def test_postgresql_target_active(pg_host):
    """postgresql.target must be active once the full startup chain completes."""
    assert pg_host.service("postgresql.target").is_running


def test_postgresql_server_running(pg_host):
    """The long-running PostgreSQL server container must be active."""
    assert pg_host.service("postgresql-server.service").is_running


def test_set_major_oneshot_completed(pg_host):
    """postgresql-set-major.service (oneshot) must have finished — not still running."""
    result = pg_host.run("systemctl is-active postgresql-set-major.service")
    assert result.stdout.strip() == "inactive"


def test_init_oneshot_completed(pg_host):
    """postgresql-init.service (oneshot) must have finished after initialization."""
    result = pg_host.run("systemctl is-active postgresql-init.service")
    assert result.stdout.strip() == "inactive"


def test_upgrade_oneshot_completed(pg_host):
    """postgresql-upgrade.service (oneshot) must have finished — no upgrade needed
    on a fresh install."""
    result = pg_host.run("systemctl is-active postgresql-upgrade.service")
    assert result.stdout.strip() == "inactive"


def test_backup_timer_scheduled(pg_host):
    """The daily backup timer must be active (scheduled)."""
    assert pg_host.service("postgresql-backup.timer").is_running


# ---------------------------------------------------------------------------
# Network / socket
# ---------------------------------------------------------------------------


def test_postgresql_port_listening(pg_host):
    """PostgreSQL must be listening on 127.0.0.1:5432 (POSTGRES_ARGS=-h 127.0.0.1)."""
    assert pg_host.socket("tcp://127.0.0.1:5432").is_listening


# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------


def test_virtiofs_mounted(pg_host):
    """The VirtioFS share must be mounted at /var/lib/virtiofs/data."""
    mount = pg_host.mount_point("/var/lib/virtiofs/data")
    assert mount.exists
    assert mount.filesystem == "virtiofs"


def test_virtiofs_postgresql_dir(pg_host):
    """/var/lib/virtiofs/data/postgresql must be created by tmpfiles.d."""
    assert pg_host.file("/var/lib/virtiofs/data/postgresql").is_directory


def test_virtiofs_backup_dir(pg_host):
    """/var/lib/virtiofs/data/postgresql/backup must be created by tmpfiles.d."""
    assert pg_host.file("/var/lib/virtiofs/data/postgresql/backup").is_directory


def test_data_dir_exists(pg_host):
    """/var/lib/quadlets/postgresql must exist with the correct ownership."""
    f = pg_host.file("/var/lib/quadlets/postgresql")
    assert f.is_directory
    assert f.user == "postgresql"
    assert f.user.uid == 10004
    assert f.group == "itix-svc"
    assert f.group.uid == 10000

def test_latest_symlink_exists(pg_host):
    """The 'latest' symlink must point to the active major-version directory."""
    link = pg_host.file("/var/lib/quadlets/postgresql/latest")
    assert link.exists
    assert link.is_symlink


def test_version_dir_exists(pg_host):
    """A directory named after PG_MAJOR_DEFAULT must exist under the data dir."""
    assert pg_host.file(
        f"/var/lib/quadlets/postgresql/{PG_MAJOR_DEFAULT}"
    ).is_directory


def test_initialized_flag_exists(pg_host):
    """The .initialized sentinel file must be written after a successful init."""
    assert pg_host.file("/var/lib/quadlets/postgresql/.initialized").exists


def test_config_env_present(pg_host):
    """/etc/quadlets/postgresql/config.env must be present and not world-readable."""
    f = pg_host.file("/etc/quadlets/postgresql/config.env")
    assert f.exists
    # mode 0600 — world and group bits must be 0
    assert f.mode & 0o077 == 0


# ---------------------------------------------------------------------------
# Database connectivity
# ---------------------------------------------------------------------------


def test_postgresql_accepts_connections(postgresql_vm, test_ssh_key):
    """PostgreSQL must respond to a trivial SQL query."""
    output = run_sql(postgresql_vm, test_ssh_key, "SELECT 1 AS probe")
    assert "1" in output


def test_postgresql_version_matches_config(postgresql_vm, test_ssh_key):
    """The running PostgreSQL server must report the version from PG_MAJOR_DEFAULT."""
    output = run_sql(postgresql_vm, test_ssh_key, "SHOW server_version")
    assert PG_MAJOR_DEFAULT in output


def test_can_create_database(postgresql_vm, test_ssh_key):
    """Should be possible to create a new database."""
    run_sql(
        postgresql_vm,
        test_ssh_key,
        "CREATE DATABASE install_test_db",
    )
    output = run_sql(
        postgresql_vm,
        test_ssh_key,
        "SELECT datname FROM pg_database WHERE datname = 'install_test_db'",
    )
    assert "install_test_db" in output
