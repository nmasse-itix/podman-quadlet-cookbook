##
## Makefile for nftables quadlet
##

# Additional nftables directories and files
TARGET_FILES += $(TARGET_CHROOT)/etc/sysconfig/nftables.conf
$(TARGET_CHROOT)/etc/sysconfig/nftables.conf: other/nftables.conf
	install -D -o root -g root -m 755 $< $@

SYSTEMD_MAIN_UNIT_NAMES = nftables.service

# Include common Makefile
include ../../scripts/common.mk

