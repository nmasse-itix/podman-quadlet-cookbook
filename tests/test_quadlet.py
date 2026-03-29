import socket
import json
import time

class TestQuadlet:
    """
    Run common tests for Quadlet cookbooks.

    All public methods are synchronous and raise on failure.
    """

    expected_services : list[dict[str, str | bool]] = [
        # Example:
        # { "name": "postgresql.service", "state": "active", "masked": False, "enabled": True, "exists": True },
    ]
    """
    Expected state of systemd services. Each dict must contain a "name" field with the service name, and may optionally contain:
    - "state": one of "active", "inactive", "failed" (optional)
    - "masked": boolean (optional)
    - "enabled": boolean (optional)
    - "exists": boolean (optional)
    Optional fields are not checked if missing.
    If "exists" is False, no other fields are checked.
    """

    expected_sockets : list[dict[str, str]] = [
        # Example:
        # { "uri": "tcp://127.0.0.1:5432", "state": "listening" },
    ]
    """
    Expected state of sockets. Each dict must contain a "uri" field with the socket URI, and a "state" field with one of "listening" or "closed".
    """

    # all fields are mandatory
    expected_ports : list[dict[str, str | int]] = [
        # Example:
        # { "number": 5432, "protocol": "tcp", "state": "closed" },
        # { "number": 22, "protocol": "tcp", "state": "open" },
    ]
    """
    Expected state of TCP ports as seen from the machine running pytest. Each dict must contain:
    - "number": port number
    - "protocol": currently only "tcp" is supported
    - "state": one of "open" (accepting connections) or "closed"
    """

    expected_files : list[dict[str, str | int]] = [
        # Example:
        # { "path": "/var/lib/quadlets/postgresql", "type": "directory", "owner": "postgresql", "group": "itix-svc", "mode": 0o755 },
    ]
    """
    Expected files on the VM. Each dict must contain:
    - "path": full path to the file
    - "type": "directory", "file" or "none" (if the file is expected to not exist)
    Optional fields:
    - "owner": expected owner username
    - "group": expected group name
    - "mode": expected file mode as an integer (e.g. 0o755)
    If an optional field is missing, it is not checked.
    """

    expected_podman_images : list[dict[str, str]] = [
        # Example:
        # { "name": "docker.io/library/postgres", "tag": "15", "state": "present" },
    ]
    """
    Expected Podman images. Each dict must contain:
    - "name": image name (e.g. "docker.io/library/postgres")
    - "tag": image tag (e.g. "15")
    - "state": one of "present" or "absent"
    """

    expected_podman_containers : list[dict[str, str | dict[str, str]]] = [
        # Example:
        # { "name": "postgresql-server", "state": "present", "pid1": { "owner": "10004", "group": "10000", "commandline": "postgres -h 127.0.0.1" } },
    ]
    """
    Expected Podman containers. Each dict must contain:
    - "name": container name
    - "state": one of "present" or "absent"
    Optional field:
    - "pid1": dict with expected properties of the container's main process (PID 1). May contain:
        - "owner": expected uid (numeric) of the process as seen from outside the container (i.e. on the host)
        - "group": expected gid (numeric) of the process as seen from outside the container (i.e. on the host)
        - "commandline": expected command line of the process
    """

    expected_main_service : str | None = None
    """
    If not None, the name of the main service to wait for before running any tests. 
    """

    expected_main_service_timeout : int = 120
    """
    If expected_main_service is set, the number of seconds to wait for it to become active before giving up and failing the tests.
    """

    def test_wait_for_main_service(self, fcos_host):
        """Wait for the expected main service to become active before running any other tests."""
        if self.expected_main_service is None:
            return
        self.wait_for_service(fcos_host, self.expected_main_service, self.expected_main_service_timeout)
    
    def wait_for_service(self, fcos_host, service: str, timeout: int = 120) -> None:
        """Block until *service* reaches the ``active`` state."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = fcos_host.run(
                f"systemctl is-active {service}", check=False
            )
            if result.stdout.strip() == "active":
                return
            time.sleep(5)
        status = fcos_host.run(
            f"systemctl status {service} --no-pager", check=False
        )
        raise TimeoutError(
            f"Service {service!r} not active after {timeout}s:\n{status.stdout}"
        )

    def wait_for_unit_done(self, fcos_host, unit: str, timeout: int = 120) -> str:
        """
        Block until a oneshot service finishes (``inactive`` or ``failed``).

        Returns:
            The final state string: ``"inactive"`` on success, ``"failed"``
            on failure.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = fcos_host.run(
                f"systemctl is-active {unit}", check=False
            )
            state = result.stdout.strip()
            if state in ("inactive", "failed"):
                return state
            time.sleep(5)
        raise TimeoutError(
            f"Unit {unit!r} did not finish within {timeout}s"
        )

    def test_expected_services(self, fcos_host):
        """The expected systemd services must be present and in the expected state."""
        self.check_expected_services(fcos_host, self.expected_services)

    def check_expected_services(self, fcos_host, expected_services: list[dict[str, str | bool]]) -> None:
        """The expected systemd services must be present and in the expected state."""
        for svc in expected_services:
            service = fcos_host.service(svc["name"])
            if "exists" in svc:
                if svc["exists"]:
                    assert service.exists, f"Service {svc['name']} does not exist"
                else:
                    assert not service.exists, f"Service {svc['name']} exists but should not"
                    continue  # if the service shouldn't exist, no need to check other properties
            if "masked" in svc:
                if svc["masked"]:
                    assert service.is_masked, f"Service {svc['name']} is not masked"
                else:
                    assert not service.is_masked, f"Service {svc['name']} is masked but should not"
            if "enabled" in svc:
                if svc["enabled"]:
                    assert service.is_enabled, f"Service {svc['name']} is not enabled"
                else:
                    assert not service.is_enabled, f"Service {svc['name']} is enabled but should not"
            if "state" in svc:
                if svc["state"] == "active":
                    assert service.is_running, f"Service {svc['name']} is not running"
                elif svc["state"] == "inactive":
                    assert not service.is_running, f"Service {svc['name']} is running but expected to be inactive"
                elif svc["state"] == "failed":
                    result = fcos_host.run(f"systemctl is-failed {svc['name']}")
                    assert result.rc == 0, f"Service {svc['name']} is not in failed state"
                else:
                    raise ValueError(f"Invalid state for service {svc['name']}: {svc['state']}")

    def test_expected_sockets(self, fcos_host):
        """The expected sockets must be present and in the expected state."""
        self.check_expected_sockets(fcos_host, self.expected_sockets)

    def check_expected_sockets(self, fcos_host, expected_sockets: list[dict[str, str]]) -> None:
        """The expected sockets must be present and in the expected state."""
        for sock in expected_sockets:
            socket = fcos_host.socket(sock["uri"])
            if sock["state"] == "listening":
                assert socket.is_listening, f"Socket {sock['uri']} is not listening"
            elif sock["state"] == "closed":
                assert not socket.is_listening, f"Socket {sock['uri']} is listening but expected to be closed"
            else:
                raise ValueError(f"Invalid state for socket {sock['uri']}: {sock['state']}")

    def test_expected_ports(self, fcos_vm):
        """The expected TCP ports must be in the expected state."""
        self.check_expected_ports(fcos_vm, self.expected_ports)

    def check_expected_ports(self, fcos_vm, expected_ports: list[dict[str, str]]) -> None:
        """The expected TCP ports must be in the expected state."""
        for port in expected_ports:
            assert port["protocol"] == "tcp", f"Unsupported protocol {port['protocol']} for port {port['number']}"
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            connect_result = s.connect_ex((fcos_vm.ip, port["number"]))
            if port["state"] == "open":
                assert connect_result == 0, f"Port {port['number']} is NOT reachable from the host on {fcos_vm.ip}!"
            elif port["state"] == "closed":
                assert connect_result != 0, f"Port {port['number']} is reachable from the host on {fcos_vm.ip} but expected to be closed"
            else:
                raise ValueError(f"Invalid state for port {port['number']}/{port['protocol']}: {port['state']}")
            s.close()

    def test_expected_files(self, fcos_host):
        """The expected files must be in the expected state."""
        self.check_expected_files(fcos_host, self.expected_files)

    def check_expected_files(self, fcos_host, expected_files: list[dict[str, str | int]]) -> None:
        """The expected files must be in the expected state."""
        for f in expected_files:
            file = fcos_host.file(f["path"])
            if f["type"] == "directory":
                assert file.is_directory, f"Expected {f['path']} to be a directory"
            elif f["type"] == "file":
                assert file.is_file, f"Expected {f['path']} to be a regular file"
            elif f["type"] == "none":
                assert not file.exists, f"Expected {f['path']} to not exist"
                continue  # if the file shouldn't exist, no need to check other properties
            else:
                raise ValueError(f"Invalid type for expected file {f['path']}: {f['type']}")

            if "owner" in f:
                assert file.user == f["owner"], f"Expected {f['path']} to be owned by {f['owner']}, but got {file.user}"
            if "group" in f:
                assert file.group == f["group"], f"Expected {f['path']} to belong to group {f['group']}, but got {file.group}"
            if "mode" in f:
                assert file.mode == f["mode"], f"Expected {f['path']} to have mode {oct(f['mode'])}, but got {oct(file.mode)}"

    def test_expected_podman_images(self, fcos_host):
        """The expected Podman images must be in the expected state."""
        self.check_expected_podman_images(fcos_host, self.expected_podman_images)

    def check_expected_podman_images(self, fcos_host, expected_podman_images: list[dict[str, str]]) -> None:
        """The expected Podman images must be in the expected state."""
        for img in expected_podman_images:
            result = fcos_host.run(f"podman image exists {img['name']}:{img['tag']}")

            if img["state"] == "present":
                assert result.rc == 0, f"Podman image {img['name']}:{img['tag']} does not exist"
            elif img["state"] == "absent":
                assert result.rc != 0, f"Podman image {img['name']}:{img['tag']} is present but expected to be absent"
            else:
                raise ValueError(f"Invalid state for Podman image {img['name']}:{img['tag']}: {img['state']}")

    def test_expected_podman_containers(self, fcos_host):
        """The expected Podman containers must be in the expected state."""
        self.check_expected_podman_containers(fcos_host, self.expected_podman_containers)

    def check_expected_podman_containers(self, fcos_host, expected_podman_containers: list[dict[str, str]]) -> None:
        """The expected Podman containers must be in the expected state."""
        for container in expected_podman_containers:
            result = fcos_host.run(f"podman container inspect {container['name']}")
            if container["state"] == "present":
                assert result.rc == 0, f"Podman container {container['name']} does not exist"
            elif container["state"] == "absent":
                assert result.rc != 0, f"Podman container {container['name']} is present but expected to be absent"
            else:
                raise ValueError(f"Invalid state for Podman container {container['name']}: {container['state']}")
            
            if result.rc == 0 and "pid1" in container:
                try:
                    result_json = json.loads(result.stdout)[0]
                except json.JSONDecodeError as e:
                    raise AssertionError(f"Failed to parse JSON output from podman inspect for container {container['name']}: {e}\nOutput was: {result_json}")
                pid = result_json["State"]["Pid"]
                result = fcos_host.run(f"ps axn -o pid,user,group,state,command -q {pid} --no-header")
                if result.rc != 0:
                    raise AssertionError(f"Failed to inspect PID 1 of container {container['name']} with nsenter: rc = {result.rc}")
                pid1_info = result.stdout.strip().split(None, 4)
                if len(pid1_info) < 5:
                    raise AssertionError(f"Unexpected output from ps for PID 1 of container {container['name']}: {result.stdout}")
                pid1_pid = pid1_info[0]
                pid1_user = pid1_info[1]
                pid1_group = pid1_info[2]
                pid1_commandline = pid1_info[4]
                assert int(pid1_pid) == pid, f"Expected PID {pid} for container {container['name']} main process, but got {pid1_pid}"
                if "owner" in container["pid1"]:
                    assert pid1_user == container["pid1"]["owner"], f"Expected PID 1 of container {container['name']} to be owned by {container['pid1']['owner']}, but got {pid1_user}"
                if "group" in container["pid1"]:
                    assert pid1_group == container["pid1"]["group"], f"Expected PID 1 of container {container['name']} to belong to group {container['pid1']['group']}, but got {pid1_group}"
                if "commandline" in container["pid1"]:
                    assert pid1_commandline == container["pid1"]["commandline"], f"Expected PID 1 of container {container['name']} to have command line {container['pid1']['commandline']}, but got {pid1_commandline}"


