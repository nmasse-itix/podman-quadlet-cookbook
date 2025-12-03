PARENT_DIR := ..
include $(PARENT_DIR)/Makefile

.PHONY: test

test: uninstall clean install
	@run() { echo $$*; "$$@"; }; \
	echo "Running Nextcloud tests..."; \
	set -Eeuo pipefail; \
	source config/config.env; \
	echo "Uploading file..."; \
	run curl -X PUT -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" --data-binary @tests/witness.txt "$${OVERWRITECLIURL}/remote.php/webdav/witness.txt" -b cookies.txt; \
	echo "Verifying file upload..."; \
	run curl -X GET -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" "$${OVERWRITECLIURL}/remote.php/webdav/witness.txt" -o /tmp/witness.txt -b cookies.txt; \
	if run cmp -s tests/witness.txt /tmp/witness.txt ; then \
		echo "File upload verified successfully!"; \
	else \
		echo "File upload verification failed!"; \
		exit 1; \
	fi

