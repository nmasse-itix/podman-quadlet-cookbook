import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_ssh_key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a temporary SSH key pair (no passphrase) for VM access."""
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
