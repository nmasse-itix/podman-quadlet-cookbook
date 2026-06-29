#!/bin/bash
set -Eeuo pipefail

MATRIX_URL="http://127.0.0.1:${TUWUNEL_PORT:-6167}"
BACKUP_RETENTION="${MATRIX_BACKUP_RETENTION:-7}"
ADMIN_ACCESS_TOKEN="${MATRIX_BACKUP_ACCESS_TOKEN}"
ADMIN_ROOM_ID="${MATRIX_BACKUP_ROOM_ID}"
BACKUP_TIMEOUT="${MATRIX_BACKUP_TIMEOUT:-300}"
BACKUP_CHECK_INTERVAL="${MATRIX_BACKUP_CHECK_INTERVAL:-30}"

MARKER="$(mktemp)"
STAGING="$(mktemp -d)"
trap 'rm -rf "$MARKER" "$STAGING"' EXIT

echo "Triggering Tuwunel online database backup..."

# Send '!admin server backup-database' to the admin room via the Matrix API
TXN_ID="backup-$(date +%s)"
curl -sSf -o /dev/null -X PUT \
    -H "Authorization: Bearer ${ADMIN_ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"msgtype":"m.text","body":"!admin server backup-database"}' \
    "${MATRIX_URL}/_matrix/client/v3/rooms/${ADMIN_ROOM_ID}/send/m.room.message/${TXN_ID}"

echo "Backup command sent. Waiting for Tuwunel to complete it..."

# Wait for new/updated files to appear under the backup source (max 5 minutes)
TIMEOUT="${BACKUP_TIMEOUT}"
ELAPSED=0
INTERVAL="${BACKUP_CHECK_INTERVAL}"
while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    if find "${BACKUP_SOURCE}" -newer "${MARKER}" -type f 2>/dev/null | grep -q .; then
        echo "Backup files detected after ${ELAPSED}s."
        break
    fi
    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "ERROR: Timed out waiting for backup after ${TIMEOUT}s." >&2
    exit 1
fi

# Find the latest numbered backup directory created by RocksDB BackupEngine
LATEST_NUM=$(ls -1 "${BACKUP_SOURCE}/private" | grep -E '^[0-9]+$' | sort -n | tail -1)
if [ -z "$LATEST_NUM" ]; then
    echo "ERROR: No numbered backup directory found in ${BACKUP_SOURCE}/private." >&2
    exit 1
fi
echo "Processing RocksDB backup #${LATEST_NUM} into restore-ready format..."

# 1. Copy and rename SST files from shared_checksum/:
#    ######_sXXXXXXXX.sst  →  ######.sst
SHARED="${BACKUP_SOURCE}/shared_checksum"
if [ -d "${SHARED}" ]; then
    for sst in "${SHARED}"/*.sst; do
        [ -f "$sst" ] || continue
        dest=$(basename "$sst" | sed 's/_s.*/.sst/')
        cp "$sst" "${STAGING}/${dest}"
    done
fi

# 2. Copy all files from the latest numbered directory (CURRENT, MANIFEST, OPTIONS, ...)
find "${BACKUP_SOURCE}/private/${LATEST_NUM}" -maxdepth 1 -type f | while read -r f; do
    cp "$f" "${STAGING}/"
done

# Archive the restore-ready staging directory
BACKUP_DATE=$(date +%Y-%m-%d_%H-%M-%S)
ARCHIVE="${BACKUP_DEST}/${BACKUP_DATE}.tar.gz"

echo "Archiving restore-ready backup to ${ARCHIVE}..."
tar -czf "${ARCHIVE}" -C "${STAGING}" .
echo "Backup archived ($(du -sh "${ARCHIVE}" | cut -f1))."

# Apply retention policy
if [ "${BACKUP_RETENTION}" -gt 0 ] && ls "${BACKUP_DEST}"/*.tar.gz > /dev/null 2>&1; then
    echo "Applying retention policy: keeping last ${BACKUP_RETENTION} backups."
    ls -1t "${BACKUP_DEST}"/*.tar.gz | tail -n "+$((BACKUP_RETENTION + 1))" | while read -r old; do
        echo "Removing old backup: ${old}"
        rm -f "${old}"
    done
fi

echo "Backup completed successfully."
