#!/bin/bash
set -Eeuo pipefail

export PGHOST=/var/run/postgresql

BACKUP_DIR=/var/lib/postgresql/backup/$(date +%Y-%m-%d_%H-%M-%S)/
mkdir -p "$BACKUP_DIR"

echo "Starting complete backup of the whole PostgreSQL server..."
pg_basebackup --pgdata=$BACKUP_DIR --format=tar --manifest-checksums=SHA256 --verbose
echo "Starting backup of individual databases..."
psql -c "SELECT datname FROM pg_database WHERE datname NOT IN ('template0', 'template1', 'postgres');" -t | while read db; do
  if [ -z "$db" ]; then
    continue
  fi
  
  echo "Backup of database $db..."
  pg_dump -c --if-exists "$db" | gzip -c > "$BACKUP_DIR/dump-$db.sql.gz"
done
echo "Backup stored in $BACKUP_DIR."

# backup rotation / retention policy
POSTGRES_BACKUP_RETENTION=${POSTGRES_BACKUP_RETENTION:-7}
if [[ "$POSTGRES_BACKUP_RETENTION" -gt 0 ]] && ls -1ct /var/lib/postgresql/backup/*/backup_manifest &>/dev/null; then
  echo "Applying backup retention policy: keeping the last $POSTGRES_BACKUP_RETENTION backups."
  ls -1ct /var/lib/postgresql/backup/*/backup_manifest | tail -n "+$((POSTGRES_BACKUP_RETENTION + 1))" | while read old_backup; do
    old_backup=$(dirname "$old_backup")
    echo "Removing old backup: $old_backup"
    rm -rf "$old_backup"
  done
else
  echo "No backup retention policy applied."
fi
