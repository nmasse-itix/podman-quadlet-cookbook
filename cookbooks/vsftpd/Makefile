##
## Makefile for Vsftpd quadlet
##

DEPENDENCIES = lego

# Vsftpd quadlet is mapped to the 10015 user (vsftpd) and 10000 group (itix-svc)
PROJECT_UID = 10015
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk

# All config file are owned by root
$(filter %.conf, $(TARGET_CONFIG_FILES) $(TARGET_EXAMPLES_CONFIG_FILES)):
	install -o root -g root -m 0644 $< $@
