import subprocess

class DNSServer:
    """
    Manages the libvirt network configuration related to DNS.
    """

    def __init__(self, network: str = "default", persistent: bool = False) -> None:
        """
        Args:
            network: The libvirt network name to configure DNS for.
            persistent: Whether to keep the DNS configuration persistent.
        """
        self.network = network
        self.persistent = persistent
        self.domain = None

    def set_domain(self, domain: str) -> None:
        """Set the domain for the DNS server."""
        self.domain = domain

    def add_host(self, ip: str, hostnames: list[str]) -> None:
        """Adds a host to the DNS server."""

        xml = f'<host ip="{ip}">'
        for hostname in hostnames:
            fqdn = f"{hostname}.{self.domain}" if self.domain else hostname
            xml += f'<hostname>{fqdn}</hostname>'
        xml += '</host>'
        result = subprocess.run(
            [
                "virsh", "net-update", self.network, "add-last", "dns-host", xml, "--live",
            ] + (["--config"] if self.persistent else []),
            capture_output=True,
            timeout=10,
            check = True,
        )

    def remove_host(self, ip: str) -> None:
        """Removes a host from the DNS server."""

        xml = f'<host ip="{ip}"/>'
        result = subprocess.run(
            [
                "virsh", "net-update", self.network, "delete", "dns-host", xml, "--live"
            ] + (["--config"] if self.persistent else []),
            capture_output=True,
            timeout=10,
            check = True,
        )

    def cleanup(self) -> None:
        """Resets the libvirt network configuration to its default state by destroying and restarting the network."""

        if not self.persistent:
            for cmd in [ "net-destroy", "net-start" ]:
                result = subprocess.run(
                    [
                        "virsh", cmd, self.network
                    ],
                    capture_output=True,
                    timeout=10,
                    check = True,
                )
