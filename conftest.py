import subprocess
from pathlib import Path

import pytest

# Persistent directory used when --keep-vm is active.
_KEEP_VM_CACHE_DIR = Path.home() / ".cache" / "podman-quadlet-cookbook-tests"


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
