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
# - ALL_DEPENDENCIES: the list of all (direct and transitive) dependencies of the project.
# - DIRECT_DEPENDENCIES: the list of all direct dependencies of the project.
# - TARGET_CHROOT: the target chroot directory containing the files to be included in the tarball.
# - BUTANE_BLOCKLIST: the path to a file containing a list of files and directories (one per line) to ignore
#                     (i.e., files and directories that are already part of the CoreOS default installation
#                     or belonging to another package).
# - SYSTEMD_START_UNITS: the list of systemd main unit names to start.
# - SYSTEMD_ENABLE_UNITS: the list of systemd unit names to enable.
# - PROJECT_USER: the project's user information (username, uid, gid, home directory).
#
# The path to of the output tarball is $1.
#

set -Eeuo pipefail

# Avoid issues with translated output of commands like stat.
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# Create a temporary directory to store intermediate files (metadata.json and content.tar)
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

# Generate the file list from the TARGET_CHROOT, excluding files and directories in the BUTANE_BLOCKLIST
declare -A files_to_include=()
inner_filelist_file="$tmp_dir/filelist.txt"
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
    echo "${rel_path#/}" >> "$inner_filelist_file"

    # Although, the absolute path is stored in the metadata file.
    files_to_include["$rel_path"]="$(stat --format='%u %g %a %F' "$path")"
done

# Generate metadata.json
metadata_file="$tmp_dir/metadata.yaml"
exec 3>&1 > "$metadata_file"
cat <<EOF
name: $PROJECT_NAME
EOF
if [ -n "${ALL_DEPENDENCIES}" ]; then
  echo "dependencies:"
  for dep in ${ALL_DEPENDENCIES};
    do echo "- $dep"
  done
else
  echo "dependencies: []"
fi
if [ -n "${DIRECT_DEPENDENCIES}" ]; then
  echo "direct_dependencies:"
  for dep in ${DIRECT_DEPENDENCIES};
    do echo "- $dep"
  done
else
  echo "direct_dependencies: []"
fi
if [ "${#files_to_include[@]}" -gt 0 ]; then
  echo "files:"
  for file in "${!files_to_include[@]}"; do
    read -r owner group mode type <<< "${files_to_include[$file]}"
    if [ "$type" == "directory" ]; then
      type="dir"
    elif [ "$type" == "regular file" ]; then
      type="file"
    else
      echo "Unsupported file type: $type for file $file" >&2
      exit 1
    fi
    cat <<EOY
- name: $file
  owner: $owner
  group: $group
  mode: "0$mode"
  type: $type
EOY
  done
else
  echo "files: []"
fi
if [ -n "${SYSTEMD_START_UNITS}" ]; then
  echo "systemd_start_units:"
  for unit in ${SYSTEMD_START_UNITS}; do
    echo "- $unit"
  done
else
  echo "systemd_start_units: []"
fi
if [ -n "${SYSTEMD_ENABLE_UNITS}" ]; then
  echo "systemd_enable_units:"
  for unit in ${SYSTEMD_ENABLE_UNITS}; do
    echo "- $unit"
  done
else
  echo "systemd_enable_units: []"
fi
if [ -n "${PROJECT_USER}" ]; then
  read -r username uid gid home <<< "${PROJECT_USER}"
  if [ "$uid" -ne 0 ] && [ "$gid" -ne 0 ]; then
    echo "users:"
    echo "- name: $username"
    echo "  uid: $uid"
    echo "  gid: $gid"
    echo "  home: $home"
  else
    echo "users: []"
  fi
else
  echo "users: []"
fi
# Restore stdout
exec 1>&3

# The list of files to be included in the outer tarball.
declare -a outer_filelist=(
  "metadata.json"
)

# Convert metadata.yaml to metadata.json
yq -o json "$metadata_file" > "$tmp_dir/metadata.json"

# Add the project's README file to the tarball if it exists.
if [ -f "README.md" ]; then
  cp "README.md" "$tmp_dir/README.md"
  outer_filelist+=("README.md")
fi

# Common tar options to ensure that the tarball is reproducible and does not contain unnecessary metadata
declare -a tar_options=(
    "--no-selinux"
    "--no-recursion"
    "--no-xattrs"
    "--no-acls"
)

# Generate content.tar with the files to be included in the tarball, preserving their relative paths and permissions.
tar -cf "$tmp_dir/content.tar" "${tar_options[@]}" -C "$TARGET_CHROOT" --verbatim-files-from --files-from="$inner_filelist_file"
outer_filelist+=("content.tar")

# Generate the final tarball.
tar -czf "$1" "${tar_options[@]}" -C "$tmp_dir" --owner=0 --group=0 "${outer_filelist[@]}"
