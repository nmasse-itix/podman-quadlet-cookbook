# Testing Guide

This project uses **pytest** with the **pytest-testinfra** plugin to run
end-to-end integration tests against real Fedora CoreOS virtual machines.

## Dependencies

Declared in `pyproject.toml`:

| Package | Purpose |
|---------|---------|
| `pytest>=8.0` | Test runner and framework |
| `pytest-testinfra>=10.1` | Infrastructure testing (services, files, sockets, ...) |
| `paramiko>=3.4` | SSH transport used by testinfra |

## Core pytest concepts

### Test discovery

pytest automatically finds tests by scanning for files named `test_*.py` and
collecting functions named `test_*` inside them. No registration is needed.

The `pyproject.toml` configuration:

```toml
[tool.pytest.ini_options]
log_cli = true
log_cli_level = "INFO"
addopts = "-v"
```

No `testpaths` is set, so pytest discovers tests in all sub-directories.
To run a specific cookbook's tests:

```bash
pytest postgresql/tests/
```

### Fixtures

A **fixture** is a function decorated with `@pytest.fixture` that prepares a
resource for a test. Fixtures are injected by naming them as test function
parameters:

```python
@pytest.fixture(scope="module")
def pg_host(...):
    return testinfra.get_host(f"ssh://root@{vm.ip}", ...)

def test_port_listening(pg_host):          # ← pg_host is injected automatically
    assert pg_host.socket("tcp://127.0.0.1:5432").is_listening
```

pytest resolves the full dependency graph: if fixture A depends on fixture B,
B is created first.

### Fixture scopes

The `scope` parameter controls how long a fixture lives:

| Scope | Lifetime |
|-------|----------|
| `"function"` (default) | Recreated for every single test |
| `"module"` | One instance per `.py` file |
| `"session"` | One instance for the entire pytest run |

In this project:

- `test_ssh_key` / `test_ssh_pubkey` are **session-scoped** — a single SSH
  key pair is generated once and shared across all tests.
- `postgresql_vm` / `pg_host` are **module-scoped** — each test file gets its
  own VM that is destroyed after the last test in that file.

### `yield` fixtures (setup + teardown)

When a fixture uses `yield`, the code before `yield` is setup and the code
after is teardown. Teardown always runs, even if a test fails.

```python
@pytest.fixture(scope="module")
def postgresql_vm(...):
    vm = FCOSVirtualMachine(...)
    vm.create()                     # ← setup
    vm.wait_ssh(...)

    yield vm                        # ← value passed to the test

    vm.destroy()                    # ← teardown (always runs)
```

### `conftest.py` — shared fixtures

`conftest.py` files are loaded automatically by pytest. Every fixture defined
in a `conftest.py` is available to all tests in the same directory and its
sub-directories.

This project has two:

| File | Scope | Contents |
|------|-------|----------|
| `conftest.py` (root) | Global | SSH key pair generation |
| `postgresql/tests/conftest.py` | PostgreSQL tests | VM creation, testinfra host, upgrade VM |

## pytest-testinfra

**testinfra** is a pytest plugin that provides a high-level Python API to
inspect the state of a remote server over SSH. A connection is established
via `testinfra.get_host()` and the resulting object exposes modules to
inspect:

| Module | Example | What it checks |
|--------|---------|----------------|
| `service` | `host.service("postgresql.target").is_running` | systemd unit state |
| `socket` | `host.socket("tcp://127.0.0.1:5432").is_listening` | open ports |
| `file` | `host.file("/etc/config").exists` | file existence, permissions, ownership |
| `mount_point` | `host.mount_point("/data").filesystem` | mounted filesystems |
| `run` | `host.run("systemctl is-active ...")` | arbitrary commands (returns `.stdout`, `.rc`) |

## Project test architecture

```
conftest.py (root)              → SSH key pair (session-scoped)
tests/
  └── vm.py                     → FCOSVirtualMachine class (create/destroy/ssh)
postgresql/tests/
  ├── conftest.py               → VM + pg_host fixtures (module-scoped)
  ├── helpers.py                → constants (PG_MAJOR_DEFAULT, credentials) + run_sql()
  ├── test_install.py           → fresh install: services, ports, filesystem, connectivity
  ├── test_backup.py            → trigger backup, verify artefacts, retention policy
  ├── test_recovery.py          → restore from backup
  └── test_upgrade.py           → major version upgrade (uses a separate VM)
```

`FCOSVirtualMachine` (in `tests/vm.py`) is a plain Python class — not a
fixture. It manages the full lifecycle of a KVM virtual machine: QCOW2 disk
creation, `virt-install`, SSH readiness polling, remote command execution via
SSH, and `virsh destroy` cleanup. Fixtures in `conftest.py` wrap this class.

## Test execution flow

Taking `test_postgresql_port_listening` as an example:

1. pytest discovers `test_install.py`.
2. It sees `test_postgresql_port_listening(pg_host)` and resolves the fixture
   chain: `pg_host` → `postgresql_vm` + `test_ssh_key`.
3. `test_ssh_key` (session-scoped) generates an Ed25519 key pair — once for
   the entire run.
4. `postgresql_vm` (module-scoped):
   - Compiles the Fedora CoreOS ignition via `make butane`.
   - Creates a KVM VM with `virt-install`.
   - Polls until SSH is reachable.
   - Waits for `postgresql.target` to become active.
5. `pg_host` connects testinfra to the VM via SSH.
6. The test runs: `pg_host.socket("tcp://127.0.0.1:5432").is_listening`.
7. After **all** tests in the module complete, `vm.destroy()` tears down the
   VM.

## Test ordering

### Module (file) order

Modules are executed in **alphabetical order** by path:

1. `test_backup.py`
2. `test_install.py`
3. `test_recovery.py`
4. `test_upgrade.py`

Since each module gets its own VM (module-scoped fixtures), there are **no
dependencies between modules**.

### Test (function) order within a module

Within a file, tests run in **source order** (top to bottom). This is
pytest's default behavior — no plugin needed.

This matters when tests have side effects. For example in `test_backup.py`:

1. `test_trigger_backup` — triggers the backup service.
2. `test_backup_completes_successfully` — waits for the service to finish.
3. `test_backup_directory_exists_in_virtiofs` — checks files created by step 1.
4. ...and so on.

Later tests depend on artefacts created by earlier ones. The ordering relies
on the declaration order in the source file.

## Pausing tests for manual inspection

### `breakpoint()` + `--pdb`

Add `breakpoint()` at any point in a test. Run with `--pdb` and `-x` (stop
at first failure):

```bash
pytest postgresql/tests/test_install.py --pdb -x
```

`--pdb` drops into the Python debugger on failure. `breakpoint()` drops into
it unconditionally. Type `c` to continue.

### `input()` + `-s`

The simplest approach — add a manual pause:

```python
def test_postgresql_port_listening(pg_host):
    assert pg_host.socket("tcp://127.0.0.1:5432").is_listening
    input("VM is running. Press Enter to continue.")
```

Run with `-s` so pytest does not capture stdin/stdout:

```bash
pytest postgresql/tests/test_install.py -s -k test_postgresql_port_listening
```

### Scope-aware pausing

The VM is destroyed after the **last** test in a module. If you pause in the
last test, the VM will be destroyed as soon as you resume. To inspect after
all tests, add a sentinel test at the end of the file:

```python
def test_zz_pause_for_inspection(postgresql_vm, test_ssh_key):
    print(f"\nVM accessible: ssh -i {test_ssh_key} root@{postgresql_vm.ip}")
    input("Inspecting... Press Enter to destroy the VM.")
```

### `-k` to target a specific test

Combine with any of the above to skip unrelated tests:

```bash
pytest postgresql/tests/test_install.py -s -k test_postgresql_port_listening
```
