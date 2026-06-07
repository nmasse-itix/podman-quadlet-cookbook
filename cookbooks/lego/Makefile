##
## Makefile for Lego quadlet
##

# Lego quadlet is mapped to the 10023 user (lego) and 10000 group (itix-svc)
PROJECT_UID = 10023
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk

TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/lego/renew-hooks.d
$(TARGET_CHROOT)/etc/quadlets/lego/renew-hooks.d:
	install -m 0700 -o root -g root -D -d $@
