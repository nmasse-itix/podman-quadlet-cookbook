TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

.PHONY: test

$(TARGET_CHROOT)/var/lib/quadlets/nextcloud/redis:
	install -m 0700 -o 0 -g 0 -d $@

$(TARGET_CHROOT)/var/lib/quadlets/nextcloud/data $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/config:
	install -m 0700 -o 82 -g 82 -d $@

install-var: $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/redis $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/data $(TARGET_CHROOT)/var/lib/quadlets/nextcloud/config

# Nextcloud depends on the PostgreSQL quadlets
.PHONY: $(TOP_LEVEL_DIR)/postgresql/postgresql.ign
$(TOP_LEVEL_DIR)/postgresql/postgresql.ign:
	make -C $(TOP_LEVEL_DIR)/postgresql postgresql.ign
fcos.ign: $(TOP_LEVEL_DIR)/postgresql/postgresql.ign

test: uninstall clean install
	@run() { echo $$*; "$$@"; }; \
	echo "Running Nextcloud tests..."; \
	set -Eeuo pipefail; \
	source config/config.env; \
	echo "Uploading file..."; \
	run curl -X PUT -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" --data-binary @tests/witness.txt "$${OVERWRITECLIURL}/remote.php/webdav/witness.txt"; \
	echo "Verifying file upload..."; \
	run curl -X GET -sSf -u "$${NEXTCLOUD_ADMIN_USER}:$${NEXTCLOUD_ADMIN_PASSWORD}" "$${OVERWRITECLIURL}/remote.php/webdav/witness.txt" -o /tmp/witness.txt; \
	if run cmp -s tests/witness.txt /tmp/witness.txt ; then \
		echo "File upload verified successfully!"; \
	else \
		echo "File upload verification failed!"; \
		exit 1; \
	fi

