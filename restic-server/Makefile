##
## Makefile for Restic REST Server quadlet
##

DEPENDENCIES = traefik

# Restic REST Server quadlet is mapped to the 10022 user (restic) and 10000 group (itix-svc)
PROJECT_UID = 10022
PROJECT_GID = 10000

TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

SYSTEMD_MAIN_UNIT_NAMES += restic-server.service
