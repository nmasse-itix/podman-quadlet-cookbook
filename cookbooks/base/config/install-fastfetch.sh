#!/bin/bash
set -Eeuo pipefail
FASTFETCH_LATEST_VERSION="$(curl -sSfL https://api.github.com/repos/fastfetch-cli/fastfetch/releases | jq -r '.[] | select(.prerelease == false and .draft == false) | .tag_name' | sort -V | tail -1)"
FASTFETCH_VERSION="${FASTFETCH_VERSION:-$FASTFETCH_LATEST_VERSION}"
FASTFETCH_BIN="/usr/local/bin/fastfetch"
declare -A ARCH_MAP=( ["aarch64"]="aarch64" ["x86_64"]="amd64" )
if [ ! -f "$FASTFETCH_BIN" ]; then
    arch="$(arch)"
    arch=${ARCH_MAP[$arch]}
    echo "Installing fastfetch $FASTFETCH_VERSION for $arch..."
    curl -sSfL https://github.com/fastfetch-cli/fastfetch/releases/download/$FASTFETCH_VERSION/fastfetch-linux-$arch.tar.gz | tar -zx --strip-components=2 -C /usr/local --no-same-owner
fi
