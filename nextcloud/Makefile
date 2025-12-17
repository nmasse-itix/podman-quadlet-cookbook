DEPENDENCIES = postgresql

TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

.PHONY: test test-set-nextcloud-major

NEXTCLOUD_MAJOR_START ?= 25
NEXTCLOUD_MAJOR_LAST ?= 31
test-set-nextcloud-major:
	sed -i 's/^NEXTCLOUD_MAJOR=.*/NEXTCLOUD_MAJOR=$(NEXTCLOUD_MAJOR_START)/' config/config.env

$(TARGET_CHROOT)/var/lib/quadlets/nextcloud/redis:
	install -m 0700 -o 0 -g 0 -d $@

$(TARGET_CHROOT)/var/lib/quadlets/nextcloud/data $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/config:
	install -m 0700 -o 82 -g 82 -d $@

$(TARGET_CHROOT)/etc/quadlets/nextcloud/www.conf: config/www.conf
	install -m 0755 -o 82 -g 82 -D $< $@

install-var: $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/redis $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/data $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/config

test: uninstall clean test-set-nextcloud-major install
	@run() { echo $$*; "$$@"; }; \
	echo "Running Nextcloud upgrade test..."; \
	set -Eeuo pipefail; \
	source config/config.env; \
	echo "Waiting for Nextcloud to be ready..."; \
	until run curl -X GET -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" "$${OVERWRITECLIURL}/status.php" &> /dev/null; do \
		echo "Nextcloud is not ready yet. Retrying in 5 seconds..."; \
		sleep 5; \
	done; \
	echo "Nextcloud is ready!"; \
	echo "Uploading file..."; \
	run curl -X PUT -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" --data-binary @tests/witness.txt "$${OVERWRITECLIURL}/remote.php/webdav/witness.txt"; \
	echo "Verifying file upload..."; \
	run curl -X GET -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" "$${OVERWRITECLIURL}/remote.php/webdav/witness.txt" -o /tmp/witness.txt; \
	if run cmp -s tests/witness.txt /tmp/witness.txt ; then \
		echo "File upload verified successfully!"; \
	else \
		echo "File upload verification failed!"; \
		exit 1; \
	fi; \
	sleep 2; \
	for (( ver=$(NEXTCLOUD_MAJOR_START); ver<$(NEXTCLOUD_MAJOR_LAST); ver++ )); do \
		nextver=$$(($$ver + 1)); \
		echo "Upgrading Nextcloud from $$ver to $$nextver..."; \
		sed -i "s/^NEXTCLOUD_MAJOR=.*/NEXTCLOUD_MAJOR=$$nextver/" /etc/quadlets/nextcloud/config.env; \
		systemctl stop nextcloud.target; \
		sleep 1; \
		systemctl start nextcloud.target; \
		echo "Waiting for Nextcloud to be ready..."; \
		until run curl -X GET -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" "$${OVERWRITECLIURL}/status.php" &> /dev/null; do \
			echo "Nextcloud is not ready yet. Retrying in 5 seconds..."; \
			sleep 5; \
		done; \
		echo "Nextcloud is ready after upgrade!"; \
		echo "Verifying file upload after upgrade..."; \
		run curl -X GET -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" "$${OVERWRITECLIURL}/remote.php/webdav/witness.txt" -o /tmp/witness.txt; \
		if run cmp -s tests/witness.txt /tmp/witness.txt ; then \
			echo "File upload verified successfully after upgrade!"; \
		else \
			echo "File upload verification failed after upgrade!"; \
			exit 1; \
		fi; \
		# Assert Nextcloud version after upgrade from status.php \
		ACTUAL_VERSION=$$(run curl -X GET -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" "$${OVERWRITECLIURL}/status.php" | grep -oP '"version":"\K[^"]+'); \
		EXPECTED_VERSION_PREFIX="$$nextver."; \
		if [[ "$$ACTUAL_VERSION" == "$$EXPECTED_VERSION_PREFIX"* ]]; then \
			echo "Nextcloud version $$ACTUAL_VERSION verified successfully after upgrade to $$nextver!"; \
		else \
			echo "Nextcloud version verification failed after upgrade to $$nextver! Expected prefix: $$EXPECTED_VERSION_PREFIX, Actual: $$ACTUAL_VERSION"; \
			exit 1; \
		fi; \
	done; \
	echo "Nextcloud upgrade tests completed successfully."
