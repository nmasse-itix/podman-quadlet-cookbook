##
## Makefile for Seedbox quadlet
##

DEPENDENCIES = traefik samba

# Seedbox quadlet is mapped to the 10017 user (seedbox) and 10000 group (itix-svc)
PROJECT_UID = 10017
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk

# browser.conf is sourced with root privileges by seedbox-waypipe.sh, so it must
# not be owned by the unprivileged user the browser itself runs as.
$(filter %/browser.conf, $(TARGET_CONFIG_FILES)):
	install -o root -g root -m 0644 $< $@
