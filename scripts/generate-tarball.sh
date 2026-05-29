#!/bin/bash

# This tool packages the current project as a tarball.
#
# The specification of the tarball is:
# - metadata.json: the project's metadata (name, dependencies, file list, unit names, etc.)
# - content.tar: the files to be installed on the target system, with their relative paths and permissions preserved.
#
# The tool takes its parameters from the environment variables defined in the Makefile:
#
# - PROJECT_NAME: the name of the project.
# - ALL_DEPS: the list of all (direct and transitive) dependencies of the project.
# - TARGET_CHROOT: the target chroot directory containing the files to be included in the tarball.
# - BUTANE_BLOCKLIST: the path to a file containing a list of files and directories (one per line) to ignore
#                     (i.e., files and directories that are already part of the CoreOS default installation
#                     or belonging to another package).
# - SYSTEMD_MAIN_UNIT_NAMES: the list of systemd main unit names to enable.
#
# The path to of the output tarball is $1.
#

set -Eeuo pipefail

# Create a temporary directory to store intermediate files (metadata.json and content.tar)
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

# Generate the file list from the TARGET_CHROOT, excluding files and directories in the BUTANE_BLOCKLIST
declare -a files_to_include=()
filelist_file="$tmp_dir/filelist.txt"
for path in $(find "$TARGET_CHROOT"); do
    rel_path="${path#$TARGET_CHROOT}"
    # Skip files & directories that are already part of the CoreOS default installation
    if grep -qxF "$rel_path" "$BUTANE_BLOCKLIST"; then
      continue
    fi

    # Skip the root directory and empty paths
    if [ -z "$rel_path" ] || [[ "$rel_path" == "/" ]]; then
      continue
    fi
    
    # The leading / is removed from the relative path in order for tar to find the file.
    echo "${rel_path#/}" >> "$filelist_file"

    # Although, the absolute path is stored in the metadata file.
    files_to_include+=("$rel_path")
done

# Generate metadata.json
metadata_file="$tmp_dir/metadata.yaml"
cat <<EOF > "$metadata_file"
name: $PROJECT_NAME
EOF
if [ -n "${ALL_DEPS}" ]; then
  echo "dependencies:" >> "$metadata_file"
  for dep in ${ALL_DEPS};
    do echo "- $dep"
  done >> "$metadata_file"
else
  echo "dependencies: []" >> "$metadata_file"
fi
if [ "${#files_to_include[@]}" -gt 0 ]; then
  echo "files:" >> "$metadata_file"
  for file in "${files_to_include[@]}"; do
    echo "- $file"
  done >> "$metadata_file"
else
  echo "files: []" >> "$metadata_file"
fi
if [ -n "${SYSTEMD_START_UNITS}" ]; then
  echo "systemd_start_units:" >> "$metadata_file"
  for unit in ${SYSTEMD_START_UNITS}; do
    echo "- $unit"
  done >> "$metadata_file"
else
  echo "systemd_start_units: []" >> "$metadata_file"
fi
if [ -n "${SYSTEMD_ENABLE_UNITS}" ]; then
  echo "systemd_enable_units:" >> "$metadata_file"
  for unit in ${SYSTEMD_ENABLE_UNITS}; do
    echo "- $unit"
  done >> "$metadata_file"
else
  echo "systemd_enable_units: []" >> "$metadata_file"
fi
# Convert metadata.yaml to metadata.json
yq -o json "$metadata_file" > "$tmp_dir/metadata.json"

# Common tar options to ensure that the tarball is reproducible and does not contain unnecessary metadata
declare -a tar_options=(
    "--no-selinux"
    "--no-recursion"
    "--no-xattrs"
    "--no-acls"
)

# Generate content.tar with the files to be included in the tarball, preserving their relative paths and permissions.
tar -cf "$tmp_dir/content.tar" "${tar_options[@]}" -C "$TARGET_CHROOT" --verbatim-files-from --files-from="$filelist_file"

# Generate the final tarball.
tar -czf "$1" "${tar_options[@]}" -C "$tmp_dir" --owner=0 --group=0 metadata.json content.tar
