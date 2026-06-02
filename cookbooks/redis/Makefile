##
## Makefile for Redis quadlet
##

# Redis runs as UID 10021 / GID 10000 on the host
PROJECT_UID = 10021
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk

TARGET_FILES += $(TARGET_CHROOT)/etc/quadlets/redis/acl.d
$(TARGET_CHROOT)/etc/quadlets/redis/acl.d:
	install -m 0700 -o root -g root -D -d $@

TARGET_REDIS_ACL_FILES = $(patsubst config/examples/acl.d/%, $(TARGET_CHROOT)/etc/quadlets/redis/acl.d/%, $(wildcard config/examples/acl.d/*))
$(TARGET_REDIS_ACL_FILES): $(TARGET_CHROOT)/etc/quadlets/redis/acl.d/%.acl: config/examples/acl.d/%.acl
	install -m 0600 -o root -g root $< $@
