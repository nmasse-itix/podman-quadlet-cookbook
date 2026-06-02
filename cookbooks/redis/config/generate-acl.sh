#!/bin/bash

set -Eeuo pipefail

if [[ $# -eq 0 ]]; then
    set -- /etc/quadlets/redis/users.acl /etc/quadlets/redis/acl.d/*.acl
fi

target_file="$1"
shift
for file in "$@"; do
    cat "$file"
    echo
done > "$target_file"

if ! grep -qE '^user +default' "$target_file"; then
    echo "Warning: 'user default' entry not found in ACL files. Disabling it in $target_file." >&2
    echo "user default off"
fi >> "$target_file"

# Remove empty lines from the generated ACL file
sed -i '/^$/d' "$target_file"

if [[ -n "${REDIS_UID:-}" && -n "${REDIS_GID:-}" ]]; then
    chown "$REDIS_UID:$REDIS_GID" "$target_file"
fi
