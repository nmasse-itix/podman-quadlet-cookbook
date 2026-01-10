##
## Makefile for Miniflux quadlet
##

DEPENDENCIES = postgresql traefik

# Miniflux quadlet is mapped to the 10010 user (miniflux) and 10000 group (itix-svc)
PROJECT_UID = 10010
PROJECT_GID = 10000

# PostgreSQL initialization scripts
TARGET_POSTGRESQL_FILES = $(patsubst other/postgresql/%, $(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%, $(wildcard other/postgresql/*))
TARGET_EXAMPLE_FILES += $(TARGET_POSTGRESQL_FILES)
$(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%.sql: other/postgresql/%.sql
	install -m 0600 -o 10004 -g 10000 $< $@

# Traefik configuration files
TARGET_TRAEFIK_FILES = $(patsubst other/traefik/%, $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%, $(wildcard other/traefik/*))
TARGET_EXAMPLE_FILES += $(TARGET_TRAEFIK_FILES)
$(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%: other/traefik/%
	install -m 0644 -o 10001 -g 10000 $< $@

TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

