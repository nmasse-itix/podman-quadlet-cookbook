##
## Makefile for PostgreSQL quadlet
##

# Project dependencies
DEPENDENCIES = virtiofs

# PostgreSQL quadlet is mapped to the 10004 user (postgres) and 10000 group (itix-svc)
PROJECT_UID = 10004
PROJECT_GID = 10000

# Include common Makefile
TOP_LEVEL_DIR := ..
include $(TOP_LEVEL_DIR)/Makefile.common

.PHONY: test test-set-pgmajor install-var

PG_MAJOR_START ?= 14
PG_MAJOR_LAST ?= 18
test-set-pgmajor:
	sed -i 's/^PG_MAJOR=.*/PG_MAJOR=$(PG_MAJOR_START)/' config/config.env

# Integration tests for PostgreSQL quadlet: backup, restore + major version upgrade (14 to 18)
test: uninstall clean test-set-pgmajor install
	@echo "Running PostgreSQL integration tests..."; \
	set -Eeuo pipefail; \
	sleep 2; \
	echo "Creating a test database and a witness table..."; \
	podman exec postgresql-server createdb test; \
	podman exec postgresql-server psql -U postgres -d test -c "CREATE TABLE witness (id SERIAL PRIMARY KEY, version VARCHAR); INSERT INTO witness (version) SELECT version();"; \
	podman exec postgresql-server psql -U postgres -d test -c "SELECT * FROM witness;"; \
	for (( ver=$(PG_MAJOR_START); ver<$(PG_MAJOR_LAST); ver++ )); do \
		echo "Running a backup..."; \
		nextver=$$(($$ver + 1)); \
		systemctl start postgresql-backup.service; \
		systemctl stop postgresql.target; \
		sleep 1; \
		rm -rf /var/lib/quadlets/postgresql/{$$ver,$$nextver,data,latest,.initialized}; \
		echo "Restoring the backup to PostgreSQL $$ver..."; \
		systemctl start postgresql.target; \
		sleep 5; \
		podman exec postgresql-server psql -U postgres -d test -c "SELECT * FROM witness;"; \
		echo "Testing upgrade from PostgreSQL $$ver to $$nextver..."; \
		systemctl stop postgresql.target; \
		sed -i "s/^PG_MAJOR=.*/PG_MAJOR=$$nextver/" /etc/quadlets/postgresql/config.env; \
		systemctl start postgresql.target; \
		sleep 5; \
		echo "Inserting line into the witness table..."; \
		podman exec postgresql-server psql -U postgres -d test -c "INSERT INTO witness (version) SELECT version();"; \
	done; \
	podman exec postgresql-server psql -U postgres -d test -c "SELECT * FROM witness;"; \
	echo "PostgreSQL upgrade tests completed."
