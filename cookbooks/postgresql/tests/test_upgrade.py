"""Test the PostgreSQL major version upgrade path: PG 14 → PG 17.

The upgrade mechanism works as follows:
  1. postgresql-set-major.service updates the ``latest`` symlink to point at
     the new PG_MAJOR directory (e.g. /var/lib/quadlets/postgresql/17/).
  2. postgresql-upgrade.service detects that
     ``latest/docker/PG_VERSION`` does not exist (the 17/ directory is
     empty) and triggers pgautoupgrade.
  3. pg_upgrade migrates data from the old directory to the new one.
  4. postgresql-server.service starts against the upgraded data.

All tests in this module share a single ``upgrade_vm`` fixture that starts
with PG_MAJOR_UPGRADE_FROM (14).  Tests are intentionally ordered to form a
sequential scenario: create data → trigger upgrade → verify outcome.
"""

from pathlib import Path

from helpers import PG_MAJOR_UPGRADE_FROM, PG_MAJOR_UPGRADE_TO, run_sql

# Sentinel table and row used to verify data survives the upgrade.
WITNESS_TABLE = "upgrade_witness"
WITNESS_VALUE = "before_upgrade"


# ---------------------------------------------------------------------------
# Pre-upgrade baseline
# ---------------------------------------------------------------------------


def test_initial_version_is_upgrade_from(upgrade_vm, test_ssh_key):
    """Precondition: the VM must be running PG_MAJOR_UPGRADE_FROM."""
    output = run_sql(upgrade_vm, test_ssh_key, "SHOW server_version")
    assert PG_MAJOR_UPGRADE_FROM in output, (
        f"Expected PG {PG_MAJOR_UPGRADE_FROM}, got: {output!r}"
    )


def test_create_witness_data(upgrade_vm, test_ssh_key):
    """Insert a row that must survive the major version upgrade."""
    run_sql(
        upgrade_vm,
        test_ssh_key,
        (
            f"CREATE TABLE IF NOT EXISTS {WITNESS_TABLE} "
            f"(id SERIAL PRIMARY KEY, message TEXT NOT NULL); "
            f"INSERT INTO {WITNESS_TABLE} (message) VALUES ('{WITNESS_VALUE}');"
        ),
    )
    output = run_sql(
        upgrade_vm,
        test_ssh_key,
        f"SELECT message FROM {WITNESS_TABLE} WHERE message = '{WITNESS_VALUE}'",
    )
    assert WITNESS_VALUE in output


# ---------------------------------------------------------------------------
# Trigger the upgrade
# ---------------------------------------------------------------------------


def test_bump_pg_major_in_config(upgrade_vm, test_ssh_key):
    """Change PG_MAJOR in config.env from UPGRADE_FROM to UPGRADE_TO."""
    upgrade_vm.ssh_run(
        f"sed -i 's/^PG_MAJOR={PG_MAJOR_UPGRADE_FROM}$/PG_MAJOR={PG_MAJOR_UPGRADE_TO}/' "
        "/etc/quadlets/postgresql/config.env",
        test_ssh_key,
    )
    # Verify the substitution worked.
    result = upgrade_vm.ssh_run(
        "grep ^PG_MAJOR= /etc/quadlets/postgresql/config.env",
        test_ssh_key,
    )
    assert f"PG_MAJOR={PG_MAJOR_UPGRADE_TO}" in result.stdout


def test_restart_postgresql_target(upgrade_vm, test_ssh_key):
    """Restart postgresql.target to kick off the upgrade chain."""
    upgrade_vm.ssh_run("systemctl restart postgresql.target", test_ssh_key)


def test_upgrade_service_completes(upgrade_vm, test_ssh_key):
    """postgresql-upgrade.service must finish in ``inactive`` state (not ``failed``).

    pgautoupgrade can take several minutes for large databases; allow up to
    10 minutes.
    """
    state = upgrade_vm.wait_for_unit_done(
        "postgresql-upgrade.service", test_ssh_key, timeout=600
    )
    assert state == "inactive", (
        f"Upgrade service ended in state {state!r}. "
        "Inspect with: systemctl status postgresql-upgrade.service --no-pager "
        "and: journalctl -u postgresql-upgrade.service"
    )


def test_server_active_after_upgrade(upgrade_vm, test_ssh_key):
    """postgresql-server.service must be active after the upgrade."""
    upgrade_vm.wait_for_service(
        "postgresql-server.service", test_ssh_key, timeout=120
    )


# ---------------------------------------------------------------------------
# Post-upgrade verification
# ---------------------------------------------------------------------------


def test_new_version_is_running(upgrade_vm, test_ssh_key):
    """PostgreSQL must now report PG_MAJOR_UPGRADE_TO as the server version."""
    output = run_sql(upgrade_vm, test_ssh_key, "SHOW server_version")
    assert PG_MAJOR_UPGRADE_TO in output, (
        f"Expected PG {PG_MAJOR_UPGRADE_TO} after upgrade, got: {output!r}"
    )


def test_witness_data_preserved(upgrade_vm, test_ssh_key):
    """The row inserted before the upgrade must still be present and correct."""
    output = run_sql(
        upgrade_vm,
        test_ssh_key,
        f"SELECT message FROM {WITNESS_TABLE} WHERE message = '{WITNESS_VALUE}'",
    )
    assert WITNESS_VALUE in output, (
        f"Witness row '{WITNESS_VALUE}' not found after upgrade. "
        f"Query returned: {output!r}"
    )


def test_old_data_dir_removed(upgrade_vm, test_ssh_key):
    """pgautoupgrade must remove the source data directory after a clean upgrade."""
    result = upgrade_vm.ssh_run(
        f"test -d /var/lib/quadlets/postgresql/{PG_MAJOR_UPGRADE_FROM}/docker",
        test_ssh_key,
        check=False,
    )
    assert result.returncode != 0, (
        f"Old data directory for PG {PG_MAJOR_UPGRADE_FROM} still exists — "
        "upgrade may not have cleaned up properly"
    )


def test_latest_symlink_points_to_new_version(upgrade_vm, test_ssh_key):
    """The ``latest`` symlink must now point at the PG_MAJOR_UPGRADE_TO directory."""
    result = upgrade_vm.ssh_run(
        "readlink /var/lib/quadlets/postgresql/latest",
        test_ssh_key,
    )
    assert PG_MAJOR_UPGRADE_TO in result.stdout, (
        f"latest symlink does not point at PG {PG_MAJOR_UPGRADE_TO}: "
        f"{result.stdout.strip()!r}"
    )


def test_new_data_dir_has_pg_version_file(upgrade_vm, test_ssh_key):
    """PG_VERSION file must exist in the new data directory (server is healthy)."""
    result = upgrade_vm.ssh_run(
        f"cat /var/lib/quadlets/postgresql/{PG_MAJOR_UPGRADE_TO}/docker/PG_VERSION",
        test_ssh_key,
    )
    assert PG_MAJOR_UPGRADE_TO in result.stdout
