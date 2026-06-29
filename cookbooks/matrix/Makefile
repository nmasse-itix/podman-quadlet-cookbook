##
## Makefile for Matrix quadlet
##

DEPENDENCIES = traefik

# Matrix quadlet is mapped to the 10031 user (matrix) and 10000 group (itix-svc)
PROJECT_UID = 10031
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk

$(TARGET_CHROOT)/etc/quadlets/matrix/tuwunel $(TARGET_CHROOT)/etc/quadlets/matrix/element-web:
	install -d -m 0700 -o $(PROJECT_UID) -g $(PROJECT_GID) -D $@
