##
## Makefile for Asterisk quadlet
##

# Asterisk and its TFTP server run as UID 10036 (asterisk) / GID 10000 (itix-svc) on the host
PROJECT_UID = 10036
PROJECT_GID = 10000

# Spool and logs of Asterisk, created by the package and not by systemd-tmpfiles:
# see the comment in tmpfiles.d/asterisk.conf.
TARGET_FILES += $(TARGET_CHROOT)/var/lib/quadlets/asterisk/spool
TARGET_FILES += $(TARGET_CHROOT)/var/lib/quadlets/asterisk/log

# Include common Makefile
include ../../scripts/common.mk

$(TARGET_CHROOT)/var/lib/quadlets/asterisk/spool $(TARGET_CHROOT)/var/lib/quadlets/asterisk/log: $(TARGET_CHROOT)/var/lib/quadlets/asterisk
	install -d -m 0750 -o $(PROJECT_UID) -g $(PROJECT_GID) $@
