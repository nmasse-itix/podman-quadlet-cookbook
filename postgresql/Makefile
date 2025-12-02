PARENT_DIR := ..
include $(PARENT_DIR)/Makefile

.PHONY: test test-set-pgmajor

PG_MAJOR_START ?= 14
PG_MAJOR_LAST ?= 18
test-set-pgmajor:
	sed -i 's/^PG_MAJOR=.*/PG_MAJOR=$(PG_MAJOR_START)/' config/config.env

test: uninstall clean test-set-pgmajor install
	@echo "Running PostgreSQL integration tests..."; \
	set -Eeuo pipefail; \
	sleep 2; \
	echo "Creating a test database and a witness table..."; \
	podman exec postgresql-server su postgres -c "createdb test"; \
	podman exec postgresql-server su postgres -c "psql -U postgres -d test -c \"CREATE TABLE witness (id SERIAL PRIMARY KEY, version VARCHAR); INSERT INTO witness (version) SELECT version();\""; \
	podman exec postgresql-server su postgres -c "psql -U postgres -d test -c \"SELECT * FROM witness;\""; \
	for (( ver=$(PG_MAJOR_START); ver<$(PG_MAJOR_LAST); ver++ )); do \
		echo "Running a backup..."; \
		nextver=$$(($$ver + 1)); \
		systemctl start postgresql-backup.service; \
		systemctl stop postgresql.target; \
		sleep 1; \
		rm -rf /var/lib/quadlets/postgresql/{$$ver,$$nextver,data,latest,.initialized}; \
		echo "Restoring the backup to PostgreSQL $$ver..."; \
		systemctl start postgresql.target; \
		sleep 2; \
		podman exec postgresql-server su postgres -c "psql -U postgres -d test -c \"SELECT * FROM witness;\""; \
		echo "Testing upgrade from PostgreSQL $$ver to $$nextver..."; \
		systemctl stop postgresql.target; \
		sed -i "s/^PG_MAJOR=.*/PG_MAJOR=$$nextver/" /etc/quadlets/postgresql/config.env; \
		systemctl start postgresql.target; \
		sleep 2; \
		echo "Inserting line into the witness table..."; \
		podman exec postgresql-server su postgres -c "psql -U postgres -d test -c \"INSERT INTO witness (version) SELECT version();\""; \
	done; \
	podman exec postgresql-server su postgres -c "psql -U postgres -d test -c \"SELECT * FROM witness;\""; \
	echo "PostgreSQL upgrade tests completed."
