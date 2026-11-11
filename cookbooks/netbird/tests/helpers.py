"""Shared expectations for the NetBird control-plane tests."""

import test_quadlet  # noqa: F401


class TestNetbird(test_quadlet.TestQuadlet):
    """Common state checks for a freshly installed NetBird control plane."""

    expected_services = [
        {"name": "netbird.target", "state": "active", "exists": True},
        {"name": "netbird-management.service", "state": "active", "exists": True},
        {"name": "netbird-signal.service", "state": "active", "exists": True},
        {"name": "netbird-relay.service", "state": "active", "exists": True},
        {"name": "netbird-dashboard.service", "state": "active", "exists": True},
        {"name": "netbird-coturn.service", "state": "active", "exists": True},
        # Dependencies must be up too.
        {"name": "postgresql.target", "state": "active", "exists": True},
        {"name": "traefik.target", "state": "active", "exists": True},
    ]

    expected_sockets = [
        # Backend listeners on the host.
        {"uri": "tcp://127.0.0.1:33073", "state": "listening"},  # management (HTTP + gRPC)
        {"uri": "tcp://127.0.0.1:10000", "state": "listening"},  # signal (gRPC + ws-proxy)
        {"uri": "tcp://127.0.0.1:33080", "state": "listening"},  # relay (WebSocket)
        {"uri": "tcp://127.0.0.1:3478", "state": "listening"},   # coturn STUN/TURN
        # Dashboard is published on loopback only.
        {"uri": "tcp://127.0.0.1:8080", "state": "listening"},
        # Traefik ingress.
        {"uri": "tcp://127.0.0.1:443", "state": "listening"},
    ]

    expected_ports = [
        # Reachable from the outside: Traefik (443), coturn STUN/TURN (3478), SSH.
        {"number": 443, "protocol": "tcp", "state": "open"},
        {"number": 3478, "protocol": "tcp", "state": "open"},
        {"number": 22, "protocol": "tcp", "state": "open"},
        # The dashboard is published on loopback only: it must NOT be reachable from outside.
        {"number": 8080, "protocol": "tcp", "state": "closed"},
    ]

    expected_files = [
        {"path": "/var/lib/quadlets/netbird", "type": "directory", "owner": "netbird", "group": "itix-svc"},
        {"path": "/var/lib/virtiofs/data/netbird/management", "type": "directory", "owner": "netbird", "group": "itix-svc", "mode": 0o700},
        {"path": "/etc/quadlets/netbird/management.json", "type": "file", "owner": "netbird", "group": "itix-svc", "mode": 0o640},
        {"path": "/etc/quadlets/netbird/management.env", "type": "file", "owner": "root", "group": "root", "mode": 0o600},
    ]

    expected_podman_images = [
        {"name": "docker.io/netbirdio/management", "tag": "0.79.0", "state": "present"},
        {"name": "docker.io/netbirdio/signal", "tag": "0.79.0", "state": "present"},
        {"name": "docker.io/netbirdio/relay", "tag": "0.79.0", "state": "present"},
        {"name": "docker.io/netbirdio/dashboard", "tag": "v2.92.0", "state": "present"},
        {"name": "docker.io/coturn/coturn", "tag": "4.6.2", "state": "present"},
    ]

    expected_podman_containers = [
        {"name": "netbird-management", "state": "present", "pid1": {"owner": "10035", "group": "10000"}},
        {"name": "netbird-signal", "state": "present", "pid1": {"owner": "10035", "group": "10000"}},
        {"name": "netbird-relay", "state": "present", "pid1": {"owner": "10035", "group": "10000"}},
        {"name": "netbird-coturn", "state": "present", "pid1": {"owner": "10035", "group": "10000"}},
        # Dashboard uses the rootful image mapped to 10035 via UIDMap.
        {"name": "netbird-dashboard", "state": "present", "pid1": {"owner": "10035", "group": "10000"}},
    ]

    expected_main_service = "netbird.target"
    expected_main_service_timeout = 300
