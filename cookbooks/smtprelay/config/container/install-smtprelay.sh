#!/bin/bash
set -Eeuo pipefail
SMTPRELAY_LATEST_VERSION="$(curl -sSfL https://api.github.com/repos/decke/smtprelay/releases | jq -r '.[] | select(.prerelease == false and .draft == false) | .tag_name' | sort -V | tail -1)"
SMTPRELAY_VERSION="${SMTPRELAY_VERSION:-$SMTPRELAY_LATEST_VERSION}"
declare -A ARCH_MAP=( ["x86_64"]="amd64" ["aarch64"]="arm64" )
arch="$(arch)"
arch=${ARCH_MAP[$arch]}
echo "Installing smtprelay $SMTPRELAY_VERSION for $arch..."
curl -sSfL https://github.com/decke/smtprelay/releases/download/$SMTPRELAY_VERSION/smtprelay-$SMTPRELAY_VERSION-linux-$arch.tar.gz | tar -zx -C /usr/local/bin --no-same-owner smtprelay
