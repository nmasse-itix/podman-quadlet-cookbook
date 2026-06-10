
SYSTEMD_MAIN_UNIT_NAMES := var-lib-virtiofs-data.mount
SYSTEMD_MAIN_UNIT_NAMES += rpm-ostree-install-qemu-guest-agent.service
SYSTEMD_MAIN_UNIT_NAMES += install-tools.service

# Include common Makefile
include ../../scripts/common.mk

$(TARGET_CHROOT)/etc/quadlets/base/install-tools.d:
	install -d -m 0755 -o root -g root -D $@

pre-requisites::
	@set -Eeuo pipefail; \
	for tool in rpm-ostree; do \
		if ! which $$tool &>/dev/null ; then \
			echo "$$tool is not installed. Please install it first." >&2; \
			exit 1; \
		fi ; \
	done
