TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

# TODO fix permissions and ownerships
$(TARGET_CHROOT)/var/lib/quadlets/nextcloud-aio/data:
	install -m 0777 -o 0 -g 0 -d $@

install-var: $(TARGET_CHROOT)/var/lib/quadlets/nextcloud-aio/data
