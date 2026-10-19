#!/bin/bash
#
# Resync the host's /etc/resolv.conf into the frozen snapshot that Podman
# bind-mounts into every Network=host container.
#
# Why: with Network=host, Podman copies /etc/resolv.conf at container *creation*
# time into .../userdata/resolv.conf and bind-mounts that copy. It is a snapshot,
# not a view: when the host's DNS servers change (DHCP renewal, renumbering,
# router replacement, ...), every running container keeps querying the old,
# now-dead resolvers — silently, until it is recreated.
#
# Fix: overwrite the snapshot's *content* in place (same inode, so the bind-mount
# stays valid). Both glibc (reloads when the file's mtime changes) and musl
# (stateless, re-reads on every lookup) then pick up the new resolvers at runtime
# with no restart and no downtime.
#
# Scope: Network=host containers ONLY. Bridged containers legitimately point at
# aardvark-dns (e.g. nameserver 10.89.0.1), which already follows the host's DNS
# live; overwriting their resolv.conf would break inter-container name resolution.

set -Eeuo pipefail

host_resolv=/etc/resolv.conf

for id in $(podman ps -q); do
    # Only touch containers that share the host network stack.
    mode="$(podman inspect --format '{{.HostConfig.NetworkMode}}' "$id" 2>/dev/null)" || continue
    [ "$mode" = host ] || continue

    snapshot="$(podman inspect --format '{{.ResolvConfPath}}' "$id" 2>/dev/null)" || continue
    [ -n "$snapshot" ] && [ -f "$snapshot" ] || continue

    if ! cmp -s "$host_resolv" "$snapshot"; then
        name="$(podman inspect --format '{{.Name}}' "$id" 2>/dev/null || echo "$id")"
        echo "Refreshing resolv.conf for container ${name} (${snapshot})"
        # In-place truncation: preserves the inode the container has bind-mounted.
        if ! cat "$host_resolv" > "$snapshot"; then
            echo "Failed to refresh resolv.conf for container ${name}!" >&2
        fi
    fi
done

exit 0
