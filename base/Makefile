TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/common.mk
SYSTEMD_MAIN_UNIT_NAMES += var-lib-virtiofs-data.mount
SYSTEMD_MAIN_UNIT_NAMES += rpm-ostree-install-qemu-guest-agent.service
SYSTEMD_MAIN_UNIT_NAMES += install-fastfetch.service

pre-requisites::
	@set -Eeuo pipefail; \
	for tool in rpm-ostree; do \
		if ! which $$tool &>/dev/null ; then \
			echo "$$tool is not installed. Please install it first." >&2; \
			exit 1; \
		fi ; \
	done
