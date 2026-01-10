##
## Makefile for Restic REST Server quadlet
##

DEPENDENCIES = traefik

# Restic REST Server quadlet is mapped to the 10022 user (restic) and 10000 group (itix-svc)
PROJECT_UID = 10022
PROJECT_GID = 10000

# Traefik configuration files
TARGET_TRAEFIK_FILES = $(patsubst other/traefik/%, $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%, $(wildcard other/traefik/*))
TARGET_EXAMPLE_FILES += $(TARGET_TRAEFIK_FILES)
$(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%: other/traefik/%
	install -m 0644 -o 10001 -g 10000 $< $@

TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

SYSTEMD_MAIN_UNIT_NAMES += restic-server.service
