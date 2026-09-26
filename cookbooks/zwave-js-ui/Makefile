##
## Makefile for Z-Wave JS UI quadlet
##

# Z-Wave JS UI runs as UID 10035 (zwave-js-ui) / GID 10000 (itix-svc) on the host
PROJECT_UID = 10035
PROJECT_GID = 10000

# Include common Makefile
include ../../scripts/common.mk

# The example security keys stand in for the operator-provided ones. Install them
# with the same 0400 mode and 10035:10000 ownership that the operator must use,
# overriding the default 0644 config-install rule for this file.
TARGET_ZWAVE_JS_UI_KEYS_EXAMPLE = $(TARGET_CHROOT)/etc/quadlets/zwave-js-ui/external-settings.json
$(TARGET_ZWAVE_JS_UI_KEYS_EXAMPLE): $(TARGET_CHROOT)/etc/quadlets/zwave-js-ui/%: config/examples/% $(TARGET_CHROOT)/etc/quadlets/zwave-js-ui
	install -m 0400 -o $(PROJECT_UID) -g $(PROJECT_GID) $< $@
