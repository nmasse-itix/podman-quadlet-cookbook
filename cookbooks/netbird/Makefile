##
## Makefile for NetBird control plane quadlet
##

DEPENDENCIES = postgresql traefik

# NetBird runs as UID 10035 (netbird) / GID 10000 (itix-svc) on the host.
PROJECT_UID = 10035
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk

# The example management.json and turnserver.conf carry secrets (data-store encryption
# key, TURN password, relay secret) and are mounted read-only into the containers, which
# run as UID 10035. Install them 0640 owned by 10035:10000 instead of the default 0644,
# so they are readable by the container user but not world-readable. The *.env files are
# handled by common.mk (root:root 0600, read by systemd as EnvironmentFile).
TARGET_NETBIRD_SECRET_EXAMPLES = $(patsubst config/examples/%, $(TARGET_CHROOT)/etc/quadlets/netbird/%, $(wildcard config/examples/management.json config/examples/turnserver.conf))
$(TARGET_NETBIRD_SECRET_EXAMPLES): $(TARGET_CHROOT)/etc/quadlets/netbird/%: config/examples/% $(TARGET_CHROOT)/etc/quadlets/netbird
	install -m 0640 -o $(PROJECT_UID) -g $(PROJECT_GID) $< $@
