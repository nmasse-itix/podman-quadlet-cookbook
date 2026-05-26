#!/bin/bash

set -Eeuo pipefail

# Execute sql script, passed via stdin (or -f flag of pqsl)
# usage: docker_process_sql [psql-cli-args]
#    ie: docker_process_sql --dbname=mydb <<<'INSERT ...'
#    ie: docker_process_sql -f my-file.sql
#    ie: docker_process_sql <my-file.sql
docker_process_sql() {
        local query_runner=( psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --no-password --no-psqlrc )
        if [ -n "$POSTGRES_DB" ]; then
                query_runner+=( --dbname "$POSTGRES_DB" )
        fi

        PGHOST= PGHOSTADDR= "${query_runner[@]}" "$@"
}

# Create the Quay database and user, and grant privileges
docker_process_sql <<-'EOSQL'
-- Initialization script for Quay database and user
CREATE USER quay WITH PASSWORD 'quay';
CREATE DATABASE quay OWNER quay;
GRANT ALL PRIVILEGES ON DATABASE quay TO quay;
EOSQL

# Connect to the Quay database and create the pg_trgm extension, which is required by Quay
export POSTGRES_USER=quay
export POSTGRES_DB=quay
docker_process_sql <<-'EOSQL'
CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOSQL
