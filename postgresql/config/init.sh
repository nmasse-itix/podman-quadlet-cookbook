#!/bin/bash

set -Eeuo pipefail

last_backup=""
for f in /var/lib/postgresql/backup/*/backup_manifest; do
  # If there are no backups, the glob pattern above won't match any files
  if [ ! -f "$f" ]; then
    continue
  fi
  
  # Check if this is the most recent backup
  if [ -z "$last_backup" ] || [ "$f" -nt "$last_backup" ]; then
    last_backup="$f"
  fi
done

if [ -n "$last_backup" ]; then
  last_backup=$(dirname "$last_backup")
  echo "Restoring from last backup: $last_backup..."
  mkdir -p "$PGDATA"
  tar -xvf "$last_backup/base.tar" -C "$PGDATA" 
  if [ -f "$last_backup/pg_wal.tar" ]; then
    mkdir -p "$PGDATA/pg_wal"
    tar -xvf "$last_backup/pg_wal.tar" -C "$PGDATA/pg_wal"
  fi
  echo "Verifying backup integrity..."
  pg_verifybackup -m "$last_backup/backup_manifest" "$PGDATA"
  echo "Setting ownership and permissions..."
  chown -R postgres:postgres "$PGDATA"
  chmod 700 "$PGDATA"
  echo "Restoration complete."
  exit 0
fi

echo "No previous backup found, initializing an empty database!"
exec /usr/local/bin/docker-ensure-initdb.sh
