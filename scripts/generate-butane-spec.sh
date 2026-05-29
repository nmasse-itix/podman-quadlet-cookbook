#!/bin/bash

#
# This tool generates a butane config file for the podman-quadlet-cookbook
# project. The generated file can be used to provision a Fedora CoreOS
# instance with all necessary quadlets and systemd units to run the
# podman-quadlet-cookbook tests.
#
# The tool takes its parameters from the environment variables defined in the Makefile:
#
# - TARGET_CHROOT: the target chroot directory containing the files to be included in the tarball.
# - BUTANE_BLOCKLIST: the path to a file containing a list of files and directories (one per line) to ignore
#                     (i.e., files and directories that are already part of the CoreOS default installation
#                     or belonging to another package).
# - SYSTEMD_MAIN_UNIT_NAMES: the list of systemd main unit names to enable.
#
# The path to of the generated butane file is $1, or stdout if $1 is not provided.
#

set -Eeuo pipefail

OUTPUT="${1:-/dev/stdout}"

cat > "$OUTPUT" <<"EOF"
variant: fcos
version: 1.4.0
storage:
  files:
EOF
for file in $(find "$TARGET_CHROOT" \! -type d); do
    rel_path="${file#$TARGET_CHROOT}"
    if grep -qxF "$rel_path" "$BUTANE_BLOCKLIST"; then

      # Skip files & directories that are already part of the CoreOS default installation
      continue
    fi
    cat >> "$OUTPUT" <<EOF
  - path: "${rel_path}"
    mode: 0$(stat -c '%a' "$file")
    user:
      id: $(stat -c '%u' "$file")
    group:
      id: $(stat -c '%g' "$file")
    # Overwrite is set to true because /etc and /var are persistent between two applications of the ignition file
    overwrite: true
    contents:
      inline: |
EOF
    sed 's/^/        /; $s/$/\n/' "$file" >> "$OUTPUT"
done
cat >> "$OUTPUT" <<"EOF"
  directories:
EOF
for dir in $(find "$TARGET_CHROOT" -type d); do
    rel_path="${dir#$TARGET_CHROOT}"
    if [ -z "$rel_path" ] || grep -qxF "$rel_path" "$BUTANE_BLOCKLIST"; then

      # Skip files & directories that are already part of the CoreOS default installation
      continue
    fi
    cat >> "$OUTPUT" <<EOF
  - path: "${rel_path}"
    mode: 0$(stat -c '%a' "$dir")
    user:
      id: $(stat -c '%u' "$dir")
    group:
      id: $(stat -c '%g' "$dir")
EOF
done

cat >> "$OUTPUT" <<"EOF"
systemd:
  units:
EOF
for unit in ${SYSTEMD_ENABLE_UNITS}; do
cat >> "$OUTPUT" <<EOF
  - name: "$unit"
    enabled: true
    mask: false
EOF
done
