##
## Makefile for Traefik quadlet
##

# Traefik quadlet is mapped to the 10001 user (traefik) and 10000 group (itix-svc)
PROJECT_UID = 10001
PROJECT_GID = 10000

TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

$(TARGET_CHROOT)/etc/quadlets/traefik/conf.d:
	install -m 0755 -o $(PROJECT_UID) -g $(PROJECT_GID) -d $@

$(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/itix-middlewares.yaml $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/ping.yaml: $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/%: other/%
	install -m 0644 -o $(PROJECT_UID) -g $(PROJECT_GID) $< $@

$(TARGET_CHROOT)/etc/quadlets/traefik/itix-admins.txt $(TARGET_CHROOT)/etc/quadlets/traefik/itix-users.txt: $(TARGET_CHROOT)/etc/quadlets/traefik/%: other/%
	install -m 0600 -o $(PROJECT_UID) -g $(PROJECT_GID) $< $@

install-config: $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d

install-examples: $(TARGET_CHROOT)/etc/quadlets/traefik/conf.d/itix-middlewares.yaml $(TARGET_CHROOT)/etc/quadlets/traefik/itix-admins.txt $(TARGET_CHROOT)/etc/quadlets/traefik/itix-users.txt
