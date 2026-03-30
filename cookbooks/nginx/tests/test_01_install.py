import textwrap
import test_quadlet  # noqa: F401

# Extra files to inject into the FCOS image for the tests in this file.
# The config.env is used to configure the nginx Quadlet.
PYTEST_FCOS_EXTRA_FILES = {
    "/etc/quadlets/nginx/config.env": (
        textwrap.dedent("""
            # This file is generated for testing purposes.
            GIT_REPO=https://github.com/nmasse-itix/podman-quadlet-cookbook.git
            GIT_BRANCH=main
            NGINX_PORT=80
            NGINX_HOST=localhost
        """),
        0,
        0,
        0o600,
    ),
}

"""
Verify that the nginx Quadlet is correctly installed and configured on a fresh VM boot.
"""
class TestNginxQuadlet(test_quadlet.TestQuadlet):
    expected_services = [
        { "name": "nginx.target", "state": "active", "exists": True },
        { "name": "nginx-server.service", "state": "active", "exists": True },
        { "name": "nginx-init.service", "state": "inactive", "exists": True },
        { "name": "nginx-update.service", "state": "inactive", "exists": True },
        { "name": "nginx-update.timer", "state": "active", "exists": True },
    ]

    expected_sockets = [
        { "uri": "tcp://127.0.0.1:80", "state": "listening" },
    ]

    expected_ports = [
        { "number": 80, "protocol": "tcp", "state": "open" },
        { "number": 22, "protocol": "tcp", "state": "open" },
    ]

    expected_files = [
        { "path": "/var/lib/quadlets/nginx", "type": "directory", "owner": "root", "group": "root", "mode": 0o755 },
        { "path": "/etc/quadlets/nginx/config.env", "type": "file", "owner": "root", "group": "root", "mode": 0o600 },
        { "path": "/var/lib/quadlets/nginx/.git", "type": "directory" },
    ]

    expected_podman_images = [
        { "name": "docker.io/library/nginx", "tag": "mainline-alpine", "state": "present" },
    ]

    expected_podman_containers = [
        { "name": "nginx-server", "state": "present" },
    ]

    expected_main_service = "nginx.target"
    expected_main_service_timeout = 300

    def test_nginx_serves_content(self, fcos_host):
        """Nginx must serve an HTTP 200 response on port 80."""
        result = fcos_host.run("curl -sSf -o /dev/null -w '%{http_code}' http://localhost/")
        assert result.rc == 0, f"curl failed with exit code {result.rc}: {result.stderr}"
        assert result.stdout.strip() == "200", f"Expected HTTP 200, got: {result.stdout.strip()}"

    def test_nginx_serves_expected_html(self, fcos_host):
        """Nginx must serve the expected HTML content cloned from the git repository."""
        result = fcos_host.run("curl -sSf http://localhost/")
        assert result.rc == 0, f"curl failed with exit code {result.rc}: {result.stderr}"
        assert "Hello World" in result.stdout, f"Expected 'Hello World' in the response, but got: {result.stdout}"

    def test_nginx_update_cycle(self, fcos_host):
        """Restarting nginx.target must trigger nginx-update (git pull) and nginx must keep serving content."""
        result = fcos_host.run("systemctl restart nginx.target")
        assert result.rc == 0, f"Failed to restart nginx.target: {result.stderr}"

        # Wait for nginx.target to become active again after the update
        self.wait_for_service(fcos_host, "nginx.target", timeout=120)

        # nginx-update.service must have run (git pull) and completed (oneshot → inactive)
        # nginx-init.service must NOT have run again (.git already exists, condition not met)
        self.check_expected_services(fcos_host, [
            { "name": "nginx-update.service", "state": "inactive", "exists": True },
            { "name": "nginx-init.service", "state": "inactive", "exists": True },
            { "name": "nginx-server.service", "state": "active", "exists": True },
        ])

        # nginx must still serve the expected content after the update cycle
        result = fcos_host.run("curl -sSf http://localhost/")
        assert result.rc == 0, f"curl failed after update cycle: {result.stderr}"
        assert "Hello World" in result.stdout, f"Expected 'Hello World' after update cycle, but got: {result.stdout}"
