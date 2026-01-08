TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

$(TARGET_CHROOT)/etc/quadlets/samba/smb.conf.d:
	install -d -m 0700 -o $(PROJECT_UID) -g $(PROJECT_GID) -D $< $@
