import pytest

# Because PostgreSQL init & upgrades can take a long time, we give the VM more resources.
@pytest.fixture(scope="package")
def fcos_vm_config() -> tuple[int, int, int, int]:
    """Default VM configuration (memory in MB, vCPUs, root disk size in GB, /var disk size in GB)."""
    return (8192, 4, 50, 100) # (memory in MB, vCPUs, disk size for / and /var in GB)

# PostgreSQL major versions to test during upgrade from PG_MAJOR_DEFAULT.
@pytest.fixture(scope="package", params=[15, 16, 17, 18])
def pg_upgrade_major(request) -> int:
    return int(request.param)

