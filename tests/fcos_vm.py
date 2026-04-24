"""
Fedora CoreOS VM lifecycle helpers for end-to-end testing.

Requires running as root (virt-install, virsh, qemu-img need root privileges).

Typical usage:
    vm = FCOSVirtualMachine(
        name="fcos-vm-abc123",
        ignition_file=Path("/tmp/fcos-test.ign"),
        virtiofs_dir=Path("/srv/fcos-test-abc123"),
    )
    vm.create()
    vm.wait_ssh(ssh_key=key_path)
    # ... run tests ...
    vm.destroy()
"""

import re
import shutil
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
import os

LIBVIRT_IMAGES_DIR = Path("/var/lib/libvirt/images")
FCOS_BASE_IMAGE = LIBVIRT_IMAGES_DIR / "library" / "fedora-coreos.qcow2"

# Butane spec version — must match the project convention.
BUTANE_VERSION = "1.4.0"

def ensure_fcos_ign(cookbook_dir: Path) -> Path:
    """Return the path to fcos-test.ign, building it via ``make butane`` if absent."""
    fcos_ign = cookbook_dir / "fcos-test.ign"
    if not fcos_ign.exists():
        subprocess.run(
            ["make", "-C", str(cookbook_dir), "butane"],
            check=True,
        )
    return fcos_ign

class FCOSIgnition:
    """
    Builds a Fedora CoreOS Ignition file, by merging multiple ignition files
    and optionally injecting extra files.

    All public methods are synchronous and raise on failure.  The caller is
    responsible for calling ``destroy()`` (typically from a pytest fixture
    teardown).
    """

    def __init__(self, ignition_files: list[Path] | None = None, ssh_key: str | None = None, extra_files: dict[str, tuple[str, str | int, str | int, int]] | None = None) -> None:
        """
        Args:
            ignition_files: List of paths to the compiled Ignition (.ign) files.
            ssh_key: Optional SSH key to inject into the Ignition.
            extra_files: Optional dictionary of extra files to inject into the Ignition.
        """
        self.ignition_files = ignition_files or list()
        self.extra_files = extra_files or dict()
        self.ssh_key = ssh_key

    def _build_extra_files_butane(self) -> str | None:
        """Build the butane file content for the extra files specified in self.extra_files."""
        if not self.extra_files:
            return None

        files = []
        for path, (content, owner, group, mode) in self.extra_files.items():
            file_desc = (
                f"    - path: {path}\n"
                f"      mode: {mode}\n"
                f"      overwrite: true\n"
                f"      user:\n"
                + (f"        id: {owner}\n" if isinstance(owner, int) else f"        name: {owner}\n") +
                f"      group:\n"
                + (f"        id: {group}\n" if isinstance(group, int) else f"        name: {group}\n") +
                f'      contents:\n'
                f'        inline: |\n'
            )
            # Prefix all lines of content with 10 spaces (2 for indentation + 8 for the literal block)
            indented_content = textwrap.indent(content + "\n", " " * 10)
            file_desc += indented_content + "\n"
            files.append(file_desc)
        header = textwrap.dedent(f"""\
            variant: fcos
            version: {BUTANE_VERSION}
            storage:
              files:
        """)
        joined = "\n".join(files)
        return f"{header}{joined}\n"

    def _build_ssh_key_butane(self) -> str | None:
        """Build the butane file content that inject the public ssh key (self.ssh_key) into the root's authorized_keys."""
        if not self.ssh_key:
            return None

        content = textwrap.dedent(f"""\
            variant: fcos
            version: {BUTANE_VERSION}
            passwd:
              users:
                - name: root
                  ssh_authorized_keys:
                    - {self.ssh_key}
        """)

        return content

    def build(self, output: Path) -> Path:
        """Build the final Ignition file by merging the base files and the extra files."""
        
        try:
            _tmpdir = tempfile.TemporaryDirectory(delete=False)
            d = Path(_tmpdir.name)

            extra_files_butane = self._build_extra_files_butane()
            ssh_key_butane = self._build_ssh_key_butane()

            test_bu = textwrap.dedent(f"""\
                variant: fcos
                version: {BUTANE_VERSION}
                systemd:
                  units:
                    # Disable & mask zincati to avoid reboots during testing.
                    - name: zincati.service
                      enabled: false
                      mask: true
                ignition:
                  config:
                    merge:
            """)

            for ign in self.ignition_files:
                test_bu += f"    - local: {ign.name}\n"
                shutil.copy(ign, d / ign.name)
            if extra_files_butane:
                extra_files_bu = d / "test_extra_files.bu"
                extra_files_bu.write_text(extra_files_butane)
                extra_files_path = d / "test_extra_files.ign"
                subprocess.run(
                    ["butane", "--strict", "-o", str(extra_files_path), str(extra_files_bu)],
                    check=True,
                    capture_output=True,
                )
                test_bu += f"    - local: {extra_files_path.name}\n"
            if ssh_key_butane:
                ssh_key_bu = d / "test_ssh_key.bu"
                ssh_key_bu.write_text(ssh_key_butane)
                ssh_key_path = d / "test_ssh_key.ign"
                subprocess.run(
                    ["butane", "--strict", "-o", str(ssh_key_path), str(ssh_key_bu)],
                    check=True,
                    capture_output=True,
                )
                test_bu += f"    - local: {ssh_key_path.name}\n"
            test_bu_path = d / "test.bu"
            test_bu_path.write_text(test_bu)

            subprocess.run(
                [
                    "butane",
                    "--strict",
                    "-d", str(d),
                    "-o", str(output),
                    str(test_bu_path),
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running butane: {e.stderr.decode()}")
            # Keep the temporary directory for debugging
            print(f"Temporary directory retained at: {_tmpdir.name}")
            raise e
        else:
            # Clean up the temporary directory if it still exists
            if Path(_tmpdir.name).exists():
                shutil.rmtree(_tmpdir.name)

        return output

class FCOSVirtualMachine:
    """Manages a Fedora CoreOS KVM virtual machine for end-to-end testing.

    All public methods are synchronous and raise on failure.  The caller is
    responsible for calling ``destroy()`` (typically from a pytest fixture
    teardown).
    """

    def __init__(self, cookbook_name: str, instance_name: str, keep: bool = False, ignition: FCOSIgnition | None = None, virtiofs_dirs: list[tuple[Path, str]] = [], vm_config: tuple[int, int, int, int] = (4096, 2, 50, 100)) -> None:
        """
        Args:
            cookbook_name: Short identifier appended to "fcos-test-" to form the
                  libvirt domain name.  Keep it unique across parallel tests.
            instance_name: Short identifier appended to the domain name to allow multiple VM for the same cookbook.
            keep: If True, the VM and its associated resources will not be automatically destroyed on teardown.  Useful for debugging.
            ignition: FCOSIgnition instance to build the Ignition (.ign) file.
            virtiofs_dirs: List of host directories and virtiofs target directories that will be exposed inside the VM.
            vm_config: Tuple containing VM configuration (memory in MB, vCPUs, root disk size in GB, /var disk size in GB).
        """
        if keep:
            self.vm_name = f"fcos-test-{cookbook_name}-{instance_name}-dev"
        else:
            self.vm_name = f"fcos-test-{cookbook_name}-{instance_name}-{os.getpid()}"
        self.ignition = ignition or FCOSIgnition()
        self.virtiofs_dirs = virtiofs_dirs
        self.vm_config = vm_config
        self._images_dir = LIBVIRT_IMAGES_DIR / self.vm_name
        self._ip: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def exists(self) -> bool:
        """Return True if a libvirt domain with this VM's name already exists."""
        result = subprocess.run(
            ["virsh", "domstate", self.vm_name],
            capture_output=True,
        )
        return result.returncode == 0

    def create(self) -> None:
        """Create disk images and start the VM via virt-install."""
        self._images_dir.mkdir(parents=True, exist_ok=True)
        for host_dir, target_dir in self.virtiofs_dirs:
            Path(host_dir).mkdir(parents=True, exist_ok=True)

        ign_dest = self._images_dir / "fcos.ign"
        self.ignition.build(ign_dest)
        ign_dest.chmod(0o644)

        (ram, vcpus, root_disk_size, var_disk_size) = self.vm_config

        # Root OS disk: copy the base image, then resize it.
        root_qcow2 = self._images_dir / "root.qcow2"
        shutil.copy(FCOS_BASE_IMAGE, root_qcow2)
        subprocess.run(
            ["qemu-img", "resize", "-f", "qcow2", str(root_qcow2), f"{root_disk_size}G"],
            check=True,
        )

        # Secondary disk for /var (keeps OS and data separate, matches common.mk).
        var_qcow2 = self._images_dir / "var.qcow2"
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", str(var_qcow2), f"{var_disk_size}G"],
            check=True,
        )

        virtiofs_options = []
        for i, (host_dir, target_dir) in enumerate(self.virtiofs_dirs):
            virtiofs_options += [
                f"--filesystem=type=mount,accessmode=passthrough,"
                f"driver.type=virtiofs,driver.queue=1024,"
                f"source.dir={host_dir},target.dir={target_dir}"
            ]

        subprocess.run(
            [
                "virt-install",
                f"--name={self.vm_name}",
                "--import",
                "--noautoconsole",
                f"--ram={ram}",
                f"--vcpus={vcpus}",
                "--os-variant=fedora-coreos-stable",
                f"--disk=path={root_qcow2},format=qcow2",
                f"--disk=path={var_qcow2},format=qcow2",
                f"--qemu-commandline=-fw_cfg name=opt/com.coreos/config,file={ign_dest}",
                "--network=network=default,model=virtio",
                "--console=pty,target.type=virtio",
                "--serial=pty",
                "--graphics=none",
                "--boot=uefi",
                "--memorybacking=access.mode=shared,source.type=memfd",
            ] + virtiofs_options,
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

    def wait_ip(self, timeout: int = 300) -> str:
        """Block until the VM has an IP address. Returns the IP address.

        Polls every 5 seconds until ``timeout`` seconds have elapsed.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ip = self.get_ip()
            if ip:
                self._ip = ip
                return ip
            time.sleep(5)
        raise TimeoutError(f"VM {self.vm_name!r} did not obtain an IP address within {timeout}s")

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
