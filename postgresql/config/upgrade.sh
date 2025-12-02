#!/bin/bash

set -Eeuo pipefail

# Find the latest PostgreSQL data directory
SOURCE_PGDATA=""
last_version=""
for version_file in /var/lib/postgresql/*/docker/PG_VERSION; do
  if [ -f "$version_file" ]; then
    version_dir=$(dirname "$version_file")
    version_major=$(cat "$version_file")
    if [ -z "$last_version" ] || [ "$version_major" -gt "$last_version" ]; then
      last_version="$version_major"
      SOURCE_PGDATA="$version_dir"
    fi
  fi
done
if [ -z "$SOURCE_PGDATA" ] || [ ! -d "$SOURCE_PGDATA" ]; then
  echo "No PostgreSQL data directory found."
  exit 1
fi
echo "Using PostgreSQL data directory: $SOURCE_PGDATA"

# Upgrade destination
TARGET_MAJOR_VERSION=${PGTARGET%%.*}
TARGET_PATH="/usr/local/bin/"
TARGET_PGDATA="/var/lib/postgresql/${TARGET_MAJOR_VERSION}/docker"

# Upgrade source
SOURCE_MAJOR_VERSION=$(cat "${SOURCE_PGDATA}/PG_VERSION")
SOURCE_PATH="/usr/local-pg${SOURCE_MAJOR_VERSION}/bin"

# Reuse functions from the official entrypoint script
source /usr/local/bin/postgres-docker-entrypoint.sh

# Because they may have been over by the sourced script, reset all flags
set -Eeuo pipefail

# if first arg looks like a flag, assume we want to run postgres server
if [ "$#" -eq 0 ] || [ "${1:0:1}" = '-' ]; then
  set -- postgres "$@"
fi

# Setup environment variables
docker_setup_env

##
## Sanity checks
##

# No need to upgrade if same major version
if [ "${SOURCE_MAJOR_VERSION}" == "${TARGET_MAJOR_VERSION}" ]; then
  echo "PostgreSQL data files version matches target version. No upgrade required."
  exit 0
fi
# No automatic upgrade support for PostgreSQL versions less than 14
if [ "${SOURCE_MAJOR_VERSION}" -lt 14 ]; then
  echo "PosgreSQL <14 is no longer supported for automatic upgrade. Please perform a manual upgrade."
  exit 1
fi
# No downgrade support
if [ "${SOURCE_MAJOR_VERSION}" -gt "${TARGET_MAJOR_VERSION}" ]; then
  echo "Downgrades are not supported. Aborting."
  exit 1
fi
# Check for concurrent upgrade processes
if [ -f "${SOURCE_PGDATA}/upgrade_in_progress.lock" ]; then
  echo "Another upgrade process seems to be running (upgrade_in_progress.lock file found). Aborting."
  exit 2
fi

# On PG v18, we have to check that data checksums, be it positive or negative, is set on the initdb args
# even when the user already provided initdb args, because otherwise Postgres v18 assumes you want checksums
# we now do this on every version to avoid one more conditional
# it also adds support for people who used Postgres with checksums before v18
if [[ -z "${POSTGRES_INITDB_ARGS:-}" || "${POSTGRES_INITDB_ARGS:-}" != *"data-checksums"* ]]; then
  DATA_CHECKSUMS_ENABLED=$(echo 'SHOW DATA_CHECKSUMS' | "${SOURCE_PATH}/postgres" --single "${@:2}" -D "${SOURCE_PGDATA}" "${POSTGRES_DB}" | grep 'data_checksums = "' | cut -d '"' -f 2)

  if [ "$DATA_CHECKSUMS_ENABLED" == "on" ]; then
    DATA_CHECKSUMS_PARAMETER="--data-checksums"
  elif [ "$TARGET_MAJOR_VERSION" -eq 18 ]; then
    # Postgres v18 enables data checksums by default and is the only version with this opt-out parameter
    DATA_CHECKSUMS_PARAMETER="--no-data-checksums"
  fi
  POSTGRES_INITDB_ARGS="${POSTGRES_INITDB_ARGS:-} ${DATA_CHECKSUMS_PARAMETER:-}"
fi

# Flags the data directory as being in the middle of an upgrade
mkdir -p "${TARGET_PGDATA}"
touch "${SOURCE_PGDATA}/upgrade_in_progress.lock"

# Now PGDATA points to the target data directory
export PGDATA="${TARGET_PGDATA}"

# Initialize target data directory
docker_verify_minimum_env
docker_init_database_dir

# Change into the PostgreSQL database directory, to avoid a pg_upgrade error about write permissions
cd "${PGDATA}"

# Perform the upgrade
echo "Upgrading PostgreSQL from version ${SOURCE_MAJOR_VERSION} to ${TARGET_MAJOR_VERSION}..."
"${TARGET_PATH}/pg_upgrade" --username="${POSTGRES_USER}" --link \
  --old-datadir "${SOURCE_PGDATA}" --new-datadir "${TARGET_PGDATA}" \
  --old-bindir "${SOURCE_PATH}" --new-bindir "${TARGET_PATH}" \
  --socketdir="/var/run/postgresql" \
  --old-options "${run_options[*]}" --new-options "${run_options[*]}"

# Re-use the pg_hba.conf and pg_ident.conf from the old data directory
cp -f "${SOURCE_PGDATA}/pg_hba.conf" "${SOURCE_PGDATA}/pg_ident.conf" "${TARGET_PGDATA}"

# Set PGPASSWORD in case password authentication is used
if [ -z "${PGPASSWORD:-}" ] && [ -n "${POSTGRES_PASSWORD:-}" ]; then
  export PGPASSWORD="${POSTGRES_PASSWORD}"
fi

# Start a temporary PostgreSQL server
docker_temp_server_start "$@"

if [ -n "${POSTGRES_UPDATE_SCRIPT:-}" ] && [ -f "${POSTGRES_UPDATE_SCRIPT}" ]; then
  echo "Running update script: ${POSTGRES_UPDATE_SCRIPT}"
  psql --username="${POSTGRES_USER}" -f "${POSTGRES_UPDATE_SCRIPT}"
fi

echo "Updating query planner stats"
declare -a database_list=( $(echo 'SELECT datname FROM pg_catalog.pg_database WHERE datistemplate IS FALSE' | psql --username="${POSTGRES_USER}" -1t --csv "${POSTGRES_DB}") )
for database in "${database_list[@]}"; do
  echo "VACUUM (ANALYZE, VERBOSE, INDEX_CLEANUP FALSE)" | psql --username="${POSTGRES_USER}" -t --csv "${database}"
done

if [[ "${PGAUTO_REINDEX:-}" != "no" ]]; then
  echo "Reindexing the databases"

  if [[ "$TARGET_MAJOR_VERSION" -le 15 ]]; then
    reindexdb --all --username="${POSTGRES_USER}"
  else
    reindexdb --all --concurrently --username="${POSTGRES_USER}"
  fi
  echo "End of reindexing the databases"
fi

# Stop the temporary PostgreSQL server
unset PGPASSWORD
docker_temp_server_stop

# Clean up lock files
rm -f "${SOURCE_PGDATA}/upgrade_in_progress.lock"
echo "PostgreSQL upgrade from version ${SOURCE_MAJOR_VERSION} to ${TARGET_MAJOR_VERSION} completed successfully."
