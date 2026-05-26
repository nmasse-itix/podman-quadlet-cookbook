# PostgreSQL initialization scripts
TARGET_POSTGRESQL_FILES = $(patsubst other/postgresql/%, $(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%, $(wildcard other/postgresql/*))
TARGET_EXAMPLE_FILES += $(TARGET_POSTGRESQL_FILES)
$(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%.sql: other/postgresql/%.sql
	install -m 0600 -o 10004 -g 10000 $< $@
$(TARGET_CHROOT)/etc/quadlets/postgresql/init.d/%.sh: other/postgresql/%.sh
	install -m 0700 -o 10004 -g 10000 $< $@
