##
## Makefile for Seedbox quadlet
##

DEPENDENCIES = traefik

# Seedbox quadlet is mapped to the 10017 user (seedbox) and 10000 group (itix-svc)
PROJECT_UID = 10017
PROJECT_GID = 10000

TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

TARGET_TRAEFIK_FILES = $(patsubst other/traefik/%, $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%, $(wildcard other/traefik/*))
TARGET_SAMBA_FILES = $(patsubst other/samba/%, $(TARGET_CHROOT)/etc/quadlets/samba/smb.conf.d/%, $(wildcard other/samba/*))

install-examples: $(TARGET_TRAEFIK_FILES) $(TARGET_SAMBA_FILES)

$(TARGET_CHROOT)/etc/quadlets/samba/smb.conf.d/%: other/samba/%
	install -m 0644 -o root -g root $< $@

$(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%: other/traefik/%
	install -m 0644 -o 10001 -g 10000 $< $@

