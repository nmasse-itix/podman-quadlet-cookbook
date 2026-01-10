##
## Makefile for Victoria Metrics Agent quadlet
##

# Victoria Metrics Agent quadlet is mapped to the 10025 user (vmagent) and 10000 group (itix-svc)
PROJECT_UID = 10025
PROJECT_GID = 10000

# Include common Makefile
TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/common.mk

SYSTEMD_MAIN_UNIT_NAMES += vmagent.service

$(TARGET_CHROOT)/etc/quadlets/vmagent/conf.d:
	install -d -m 0700 -o $(PROJECT_UID) -g $(PROJECT_GID) -D $< $@
