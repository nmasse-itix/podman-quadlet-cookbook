#!/bin/bash

set -Eeuo pipefail

cat <<'EOF'
variant: fcos
version: 1.4.0
ignition:
  config:
    merge:
EOF
for dep in "$@"; do
    echo "    - local: ${dep}.ign"
    echo "    - local: ${dep}-examples.ign"
done
echo "    - local: local.ign"
