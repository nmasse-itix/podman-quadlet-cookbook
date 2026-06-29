#!/bin/bash
set -Eeuo pipefail

# Find the latest restore-ready backup archive
LATEST=$(ls -1t "${BACKUP_SOURCE}"/*.tar.gz 2>/dev/null | head -1 || true)
if [ -z "$LATEST" ]; then
    echo "No backup archive found in ${BACKUP_SOURCE}, starting with a fresh database."
    exit 0
fi

echo "Restoring database from ${LATEST}..."
tar -xzf "${LATEST}" -C "${DB_DEST}"
echo "Restore completed. Database ready at ${DB_DEST}."
