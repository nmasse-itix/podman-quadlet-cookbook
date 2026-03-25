"""Test PostgreSQL automatic crash recovery.

Scenarios covered:
  1. Container crash (SIGKILL via ``podman kill``) → systemd restarts the
     service automatically (Restart=always, RestartSec=10).
  2. Hard VM reboot → all services start cleanly and data is intact.

All tests share the module-scoped ``postgresql_vm`` fixture.  Because some
tests are destructive (they kill the container), they are intentionally
sequenced: create data → crash → verify recovery → create more data →
reboot → verify recovery.
"""

import time

from helpers import run_sql

# Data written before the crash that must survive each recovery scenario.
CRASH_WITNESS_TABLE = "crash_witness"
CRASH_WITNESS_VALUE = "before_crash"

REBOOT_WITNESS_TABLE = "reboot_witness"
REBOOT_WITNESS_VALUE = "before_reboot"


# ---------------------------------------------------------------------------
# Scenario 1: container crash
# ---------------------------------------------------------------------------


def test_server_running_before_crash(pg_host):
    """Precondition: postgresql-server.service must be active before we crash it."""
    assert pg_host.service("postgresql-server.service").is_running


def test_create_data_before_crash(postgresql_vm, test_ssh_key):
    """Insert a row that must survive the container crash."""
    run_sql(
        postgresql_vm,
        test_ssh_key,
        (
            f"CREATE TABLE IF NOT EXISTS {CRASH_WITNESS_TABLE} "
            f"(id SERIAL PRIMARY KEY, message TEXT NOT NULL); "
            f"INSERT INTO {CRASH_WITNESS_TABLE} (message) "
            f"VALUES ('{CRASH_WITNESS_VALUE}');"
        ),
    )


def test_kill_postgresql_container(postgresql_vm, test_ssh_key):
    """Simulate a process crash by sending SIGKILL to the container.

    ``podman kill`` delivers SIGKILL to the container's PID 1.  Systemd will
    detect the exit and restart the service after RestartSec=10 seconds.
    """
    postgresql_vm.ssh_run(
        "podman kill --signal SIGKILL postgresql-server",
        test_ssh_key,
    )


def test_service_restarts_automatically(postgresql_vm, test_ssh_key):
    """postgresql-server.service must be active again after the crash.

    Allow up to 60 seconds: systemd waits RestartSec=10 s before restarting,
    then the container start-up and health check take additional time.
    """
    # Brief pause to let systemd register the exit before we start polling.
    time.sleep(5)
    postgresql_vm.wait_for_service(
        "postgresql-server.service", test_ssh_key, timeout=120
    )


def test_data_intact_after_crash_recovery(postgresql_vm, test_ssh_key):
    """Rows written before the crash must be present after automatic recovery."""
    output = run_sql(
        postgresql_vm,
        test_ssh_key,
        f"SELECT message FROM {CRASH_WITNESS_TABLE} "
        f"WHERE message = '{CRASH_WITNESS_VALUE}'",
    )
    assert CRASH_WITNESS_VALUE in output, (
        f"Crash witness row not found after recovery. Query returned: {output!r}"
    )


def test_target_still_active_after_crash(pg_host):
    """postgresql.target must remain active after the container recovery."""
    assert pg_host.service("postgresql.target").is_running


# ---------------------------------------------------------------------------
# Scenario 2: hard reboot
# ---------------------------------------------------------------------------


def test_create_data_before_reboot(postgresql_vm, test_ssh_key):
    """Insert a row that must survive a full VM reboot."""
    run_sql(
        postgresql_vm,
        test_ssh_key,
        (
            f"CREATE TABLE IF NOT EXISTS {REBOOT_WITNESS_TABLE} "
            f"(id SERIAL PRIMARY KEY, message TEXT NOT NULL); "
            f"INSERT INTO {REBOOT_WITNESS_TABLE} (message) "
            f"VALUES ('{REBOOT_WITNESS_VALUE}');"
        ),
    )


def test_reboot_vm(postgresql_vm, test_ssh_key):
    """Trigger a graceful OS reboot.  SSH will temporarily drop."""
    postgresql_vm.ssh_run("systemctl reboot", test_ssh_key, check=False)
    # Wait for the VM to go down before polling for SSH again.
    time.sleep(15)


def test_ssh_available_after_reboot(postgresql_vm, test_ssh_key):
    """SSH must become available again within 5 minutes of the reboot."""
    # Reset the cached IP so wait_ssh re-probes it.
    postgresql_vm._ip = None
    postgresql_vm.wait_ssh(ssh_key=test_ssh_key, timeout=300)


def test_postgresql_target_active_after_reboot(postgresql_vm, test_ssh_key):
    """postgresql.target must come up automatically on reboot (enabled in ignition)."""
    postgresql_vm.wait_for_service(
        "postgresql.target", ssh_key=test_ssh_key, timeout=300
    )


def test_data_intact_after_reboot(postgresql_vm, test_ssh_key):
    """Rows written before the reboot must still be present after boot."""
    output = run_sql(
        postgresql_vm,
        test_ssh_key,
        f"SELECT message FROM {REBOOT_WITNESS_TABLE} "
        f"WHERE message = '{REBOOT_WITNESS_VALUE}'",
    )
    assert REBOOT_WITNESS_VALUE in output, (
        f"Reboot witness row not found. Query returned: {output!r}"
    )


def test_crash_witness_also_intact_after_reboot(postgresql_vm, test_ssh_key):
    """Data written before the crash must also survive the subsequent reboot."""
    output = run_sql(
        postgresql_vm,
        test_ssh_key,
        f"SELECT message FROM {CRASH_WITNESS_TABLE} "
        f"WHERE message = '{CRASH_WITNESS_VALUE}'",
    )
    assert CRASH_WITNESS_VALUE in output
