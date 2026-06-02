# Redis ACL fragments
TARGET_REDIS_FILES = $(patsubst other/redis/%.acl, $(TARGET_CHROOT)/etc/quadlets/redis/acl.d/%.acl, $(wildcard other/redis/*.acl))
TARGET_EXAMPLE_FILES += $(TARGET_REDIS_FILES)
$(TARGET_CHROOT)/etc/quadlets/redis/acl.d/%.acl: other/redis/%.acl
	install -D -m 0644 -o root -g root $< $@
