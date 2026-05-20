##
## Makefile for Traefik quadlet
##

# Traefik quadlet is mapped to the 10001 user (traefik) and 10000 group (itix-svc)
PROJECT_UID = 10001
PROJECT_GID = 10000

TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d
$(TARGET_CHROOT)/etc/quadlets/traefik/conf.d:
	install -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) -D -d $@

# Include common Makefile
include ../../scripts/common.mk
