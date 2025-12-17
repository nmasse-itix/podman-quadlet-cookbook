#!/bin/bash

#
# This tool generates a butane config file for the podman-quadlet-cookbook
# project. The generated file can be used to provision a Fedora CoreOS
# instance with all necessary quadlets and systemd units to run the
# podman-quadlet-cookbook tests.
#
# It takes the following parameters:
#   - The target chroot directory where the quadlets and systemd units
#     have been installed.
#   - The list of systemd main unit names to enable.
#
# It outputs the butane config file to stdout.
#

set -Eeuo pipefail

TARGET_CHROOT="$1"
SYSTEMD_MAIN_UNIT_NAMES="${@:2}"

cat <<"EOF"
variant: fcos
version: 1.4.0
storage:
  files:
EOF
for file in $(find "$TARGET_CHROOT" \! -type d); do
    rel_path="${file#$TARGET_CHROOT}"
    cat <<EOF
  - path: "${rel_path}"
    mode: 0$(stat -c '%a' "$file")
    user:
      id: $(stat -c '%u' "$file")
    group:
      id: $(stat -c '%g' "$file")
    contents:
      inline: |
EOF
    sed 's/^/        /; $s/$/\n/' "$file"
done
cat <<"EOF"
  directories:
EOF
for dir in $(find "$TARGET_CHROOT" -type d); do
    rel_path="${dir#$TARGET_CHROOT}"
    if [[ "$rel_path" != "/var/lib/quadlets/"* ]] && [[ "$rel_path" != "/etc/quadlets/"* ]] \
        && [[ "$rel_path" != "/etc/systemd/system/"* ]] && [[ "$rel_path" != "/etc/containers/systemd/"* ]] \
        && [[ "$rel_path" != "/etc/tmpfiles.d/"* ]] && [[ "$rel_path" != "/etc/sysctl.d/"* ]]; then

      # Skip files & directories that are already part of the CoreOS default installation
      continue
    fi
    cat <<EOF
  - path: "${rel_path}"
    mode: 0$(stat -c '%a' "$dir")
    user:
      id: $(stat -c '%u' "$dir")
    group:
      id: $(stat -c '%g' "$dir")
EOF
done

cat <<"EOF"
systemd:
  units:
EOF
for unit in ${SYSTEMD_MAIN_UNIT_NAMES}; do
cat <<EOF
  - name: "$unit"
    enabled: true
    mask: false
EOF
done
