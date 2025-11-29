#!/bin/bash
set -Eeuo pipefail

export PGHOST=/var/run/postgresql

BACKUP_DIR=/backup/$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"

psql -c "SELECT datname FROM pg_database WHERE datname NOT IN ('template0', 'template1', 'postgres');" -t | while read db; do
  if [ -z "$db" ]; then
    continue
  fi
  
  echo "Backup of database $db..."
  pg_dump -c --if-exists "$db" | gzip -c > "$BACKUP_DIR/dump-$db.sql.gz"
done
echo "Complete backup of the whole PostgreSQL server..."
pg_basebackup -D "$BACKUP_DIR/pg_basebackup"
echo "Backups stored in $BACKUP_DIR"
