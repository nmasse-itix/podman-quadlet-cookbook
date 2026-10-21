##
## Makefile for Lego quadlet
##

# Lego quadlet is mapped to the 10023 user (lego) and 10000 group (itix-svc)
PROJECT_UID = 10023
PROJECT_GID = 10000

# .path units are not picked up by common.mk's wildcard (only .service/.target/
# .timer/.mount), so install it explicitly. It is started by lego.target.
TARGET_FILES += $(TARGET_CHROOT)/etc/systemd/system/lego-hooks.path

# Include common Makefile
include ../../scripts/common.mk

TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/lego/renew-hooks.d
$(TARGET_CHROOT)/etc/quadlets/lego/renew-hooks.d:
	install -m 0700 -o root -g root -D -d $@
