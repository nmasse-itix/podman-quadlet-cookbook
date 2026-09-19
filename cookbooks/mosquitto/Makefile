##
## Makefile for Mosquitto quadlet
##

DEPENDENCIES = traefik

# Mosquitto runs as UID 10033 (mosquitto) / GID 10000 (itix-svc) on the host
PROJECT_UID = 10033
PROJECT_GID = 10000

# The conf.d directory must exist even when empty: mosquitto's include_dir fails if the
# directory is missing. Ship it as a packaged (persistent) directory.
TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/mosquitto/conf.d

# Include common Makefile
include ../../scripts/common.mk

$(TARGET_CHROOT)/etc/quadlets/mosquitto/conf.d:
	install -d -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) -D $@

# The example password and ACL files stand in for the operator-provided secrets. Install
# them with the same 0640 mode and 10033:10000 ownership that the operator must use,
# overriding the default 0644 config-install rule for these two files.
TARGET_MOSQUITTO_SECRET_EXAMPLES = $(patsubst config/examples/%, $(TARGET_CHROOT)/etc/quadlets/mosquitto/%, $(wildcard config/examples/passwd config/examples/acl))
$(TARGET_MOSQUITTO_SECRET_EXAMPLES): $(TARGET_CHROOT)/etc/quadlets/mosquitto/%: config/examples/% $(TARGET_CHROOT)/etc/quadlets/mosquitto
	install -m 0640 -o $(PROJECT_UID) -g $(PROJECT_GID) $< $@
