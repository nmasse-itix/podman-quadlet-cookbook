"""Fedora CoreOS VM lifecycle helpers for end-to-end testing.

Requires running as root (virt-install, virsh, qemu-img need root privileges).

Typical usage:
    vm = FCOSVirtualMachine(
        name="postgresql-abc123",
        ignition_file=Path("/tmp/fcos-test.ign"),
        virtiofs_dir=Path("/srv/fcos-test-postgresql-abc123"),
    )
    vm.create()
    vm.wait_ssh(ssh_key=key_path)
    vm.wait_for_service("postgresql.target", ssh_key=key_path)
    # ... run tests ...
    vm.destroy()
"""

import base64
import re
import shutil
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path

LIBVIRT_IMAGES_DIR = Path("/var/lib/libvirt/images")
FCOS_BASE_IMAGE = LIBVIRT_IMAGES_DIR / "library" / "fedora-coreos.qcow2"

# Butane spec version — must match the project convention.
BUTANE_VERSION = "1.4.0"

def ensure_fcos_ign(cookbook_dir: Path) -> Path:
    """Return the path to fcos.ign, building it via ``make butane`` if absent."""
    fcos_ign = cookbook_dir / "fcos.ign"
    if not fcos_ign.exists():
        subprocess.run(
            ["make", "-C", str(cookbook_dir), "butane"],
            check=True,
        )
    return fcos_ign


def build_test_ignition(
    base_ignition: Path,
    ssh_pubkey: str,
    output: Path,
    config_env_overrides: dict[str, str] | None = None,
    extra_files: dict[str, tuple[str, int]] | None = None,
) -> Path:
    """Build a test ignition file by overlaying the cookbook's fcos.ign.

    The overlay:
      - Merges the base cookbook ignition (fcos.ign).
      - Adds the test SSH public key to the root user so the test runner can
        SSH in (FCOS allows root login with keys via PermitRootLogin
        prohibit-password).
      - Optionally patches /etc/quadlets/postgresql/config.env via
        ``config_env_overrides`` (merged on top of whatever the base ignition
        already sets).
      - Optionally injects arbitrary extra files via ``extra_files``:
        ``{"/path/on/vm": ("file content", 0o644)}``.

    Args:
        base_ignition: Path to the pre-built fcos.ign for the cookbook.
        ssh_pubkey: Ed25519 public key string to inject for root.
        output: Destination path for the compiled test ignition.
        config_env_overrides: Key/value pairs to override in config.env.
            The full config.env is re-written with these values merged on
            top of the defaults from the base ignition.
        extra_files: Additional files to inject into the VM image.

    Returns:
        ``output`` path.
    """
    with tempfile.TemporaryDirectory() as _tmpdir:
        d = Path(_tmpdir)

        # butane resolves "local:" references relative to the directory passed
        # via -d; copy the base ignition there.
        shutil.copy(base_ignition, d / "base.ign")

        # Build the storage.files section of the overlay.
        storage_section = _build_storage_section(config_env_overrides, extra_files)

        overlay_bu = textwrap.dedent(f"""\
            variant: fcos
            version: {BUTANE_VERSION}
            ignition:
              config:
                merge:
                  - local: base.ign
            passwd:
              users:
                - name: root
                  ssh_authorized_keys:
                    - {ssh_pubkey}
            systemd:
              units:
              # Disable & mask zincati to avoid reboots during testing.
              - name: zincati.service
                enabled: false
                mask: true
        """)
        
        if storage_section:
            overlay_bu += storage_section

        overlay_bu_path = d / "test-overlay.bu"
        overlay_bu_path.write_text(overlay_bu)

        subprocess.run(
            [
                "butane",
                "--strict",
                "-d", str(d),
                "-o", str(output),
                str(overlay_bu_path),
            ],
            check=True,
        )

    return output


def _build_storage_section(
    config_env_overrides: dict[str, str] | None,
    extra_files: dict[str, tuple[str, int]] | None,
) -> str:
    """Return a Butane ``storage:`` YAML block (or empty string if nothing to inject)."""
    files = []

    if config_env_overrides:
        content = "\n".join(f"{k}={v}" for k, v in config_env_overrides.items()) + "\n"
        files.append(
            _butane_file("/etc/quadlets/postgresql/config.env", content, 0o600)
        )

    if extra_files:
        for path, (content, mode) in extra_files.items():
            files.append(_butane_file(path, content, mode))

    if not files:
        return ""

    joined = "\n".join(files)
    return f"storage:\n  files:\n{joined}\n"


def _butane_file(path: str, content: str, mode: int) -> str:
    """Return a Butane file entry using a base64 data URI (avoids YAML quoting)."""
    b64 = base64.b64encode(content.encode()).decode()
    return (
        f"    - path: {path}\n"
        f"      mode: {mode}\n"
        f"      contents:\n"
        f'        source: "data:text/plain;base64,{b64}"\n'
    )


class FCOSVirtualMachine:
    """Manages a Fedora CoreOS KVM virtual machine for end-to-end testing.

    All public methods are synchronous and raise on failure.  The caller is
    responsible for calling ``destroy()`` (typically from a pytest fixture
    teardown).
    """

    def __init__(self, name: str, ignition_file: Path, virtiofs_dir: Path) -> None:
        """
        Args:
            name: Short identifier appended to "fcos-test-" to form the
                  libvirt domain name.  Keep it unique across parallel tests.
            ignition_file: Path to the compiled Ignition (.ign) file.
            virtiofs_dir: Host directory that will be exposed inside the VM
                          at /var/lib/virtiofs/data via VirtioFS.
        """
        self.name = name
        self.vm_name = f"fcos-test-{name}"
        self.ignition_file = Path(ignition_file)
        self.virtiofs_dir = Path(virtiofs_dir)
        self._images_dir = LIBVIRT_IMAGES_DIR / self.vm_name
        self._ip: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def create(self) -> None:
        """Create disk images and start the VM via virt-install."""
        self._images_dir.mkdir(parents=True, exist_ok=True)
        self.virtiofs_dir.mkdir(parents=True, exist_ok=True)

        ign_dest = self._images_dir / "fcos.ign"
        shutil.copy(self.ignition_file, ign_dest)
        ign_dest.chmod(0o644)

        # Root OS disk: copy from the shared base QCOW2 image.
        root_qcow2 = self._images_dir / "root.qcow2"
        shutil.copy(FCOS_BASE_IMAGE, root_qcow2)

        # Secondary disk for /var (keeps OS and data separate, matches common.mk).
        var_qcow2 = self._images_dir / "var.qcow2"
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", str(var_qcow2), "100G"],
            check=True,
        )

        subprocess.run(
            [
                "virt-install",
                f"--name={self.vm_name}",
                "--import",
                "--noautoconsole",
                "--ram=4096",
                "--vcpus=2",
                "--os-variant=fedora-coreos-stable",
                f"--disk=path={root_qcow2},format=qcow2,size=50",
                f"--disk=path={var_qcow2},format=qcow2",
                f"--qemu-commandline=-fw_cfg name=opt/com.coreos/config,file={ign_dest}",
                "--network=network=default,model=virtio",
                "--console=pty,target.type=virtio",
                "--serial=pty",
                "--graphics=none",
                "--boot=uefi",
                "--memorybacking=access.mode=shared,source.type=memfd",
                (
                    f"--filesystem=type=mount,accessmode=passthrough,"
                    f"driver.type=virtiofs,driver.queue=1024,"
                    f"source.dir={self.virtiofs_dir},target.dir=data"
                ),
            ],
            check=True,
        )

    def destroy(self) -> None:
        """Forcefully stop and delete the VM and all associated disk images."""
        subprocess.run(["virsh", "destroy", self.vm_name], capture_output=True)
        subprocess.run(
            ["virsh", "undefine", self.vm_name, "--nvram"],
            capture_output=True,
        )
        if self._images_dir.exists():
            shutil.rmtree(self._images_dir)
        if self.virtiofs_dir.exists():
            shutil.rmtree(self.virtiofs_dir)

    # ------------------------------------------------------------------
    # Readiness polling
    # ------------------------------------------------------------------

    def get_ip(self) -> str | None:
        """Return the VM's primary IPv4 address reported by virsh, or None."""
        result = subprocess.run(
            ["virsh", "domifaddr", self.vm_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", result.stdout)
        return match.group(1) if match else None

    @property
    def ip(self) -> str:
        if self._ip is None:
            self._ip = self.get_ip()
        if self._ip is None:
            raise RuntimeError(f"VM {self.vm_name!r} has no IP address yet")
        return self._ip

    def wait_ssh(self, ssh_key: Path, timeout: int = 300) -> str:
        """Block until SSH is reachable. Returns the IP address.

        Polls every 5 seconds until ``timeout`` seconds have elapsed.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ip = self.get_ip()
            if ip:
                try:
                    result = subprocess.run(
                        [
                            "ssh",
                            "-i", str(ssh_key),
                            "-o", "StrictHostKeyChecking=no",
                            "-o", "UserKnownHostsFile=/dev/null",
                            "-o", "ConnectTimeout=5",
                            "-o", "BatchMode=yes",
                            f"root@{ip}",
                            "true",
                        ],
                        capture_output=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        self._ip = ip
                        return ip
                except subprocess.TimeoutExpired:
                    pass
            time.sleep(5)
        raise TimeoutError(
            f"VM {self.vm_name!r} did not become SSH-ready within {timeout}s"
        )

    def wait_for_service(
        self, service: str, ssh_key: Path, timeout: int = 120
    ) -> None:
        """Block until *service* reaches the ``active`` state."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.ssh_run(
                f"systemctl is-active {service}", ssh_key, check=False
            )
            if result.stdout.strip() == "active":
                return
            time.sleep(5)
        status = self.ssh_run(
            f"systemctl status {service} --no-pager", ssh_key, check=False
        )
        raise TimeoutError(
            f"Service {service!r} not active after {timeout}s:\n{status.stdout}"
        )

    def wait_for_unit_done(
        self, service: str, ssh_key: Path, timeout: int = 120
    ) -> str:
        """Block until a oneshot service finishes (``inactive`` or ``failed``).

        Returns:
            The final state string: ``"inactive"`` on success, ``"failed"``
            on failure.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.ssh_run(
                f"systemctl is-active {service}", ssh_key, check=False
            )
            state = result.stdout.strip()
            if state in ("inactive", "failed"):
                return state
            time.sleep(5)
        raise TimeoutError(
            f"Service {service!r} did not finish within {timeout}s"
        )

    # ------------------------------------------------------------------
    # Remote execution
    # ------------------------------------------------------------------

    def ssh_run(
        self,
        command: str,
        ssh_key: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a shell command in the VM via SSH.

        Args:
            command: Shell command string passed to the remote bash.
            ssh_key: Path to the private key used for authentication.
            check: If True (default), raise RuntimeError on non-zero exit.

        Returns:
            CompletedProcess with stdout/stderr as text.
        """
        result = subprocess.run(
            [
                "ssh",
                "-i", str(ssh_key),
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"root@{self.ip}",
                command,
            ],
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                f"SSH command failed (exit {result.returncode}): {command!r}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result
