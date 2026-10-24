#!/bin/bash

set -Eeuo pipefail

# Usage: default-butane-spec.sh <ignition file>... <local.ign>
#
# Butane inlines the "local" files as data URLs and rejects duplicate entries.
# So, ignition files whose content is identical to a previous one (typically
# the empty "-examples" ignition files, or an empty local.ign) are skipped.
# Merging the same config twice would be a no-op anyway.

cat <<'EOF'
variant: fcos
version: 1.4.0
ignition:
  config:
    merge:
EOF
declare -A seen=()
for ign in "$@"; do
    checksum="$(sha256sum "$ign" | cut -d' ' -f1)"
    if [ -n "${seen[$checksum]:-}" ]; then
        echo "Skipping $(basename "$ign"): same content as ${seen[$checksum]}." >&2
        continue
    fi
    seen[$checksum]="$(basename "$ign")"
    echo "    - local: $(basename "$ign")"
done
