#!/bin/sh
#
# Bootstrap Home Assistant's /config on first start.
#
# Home Assistant owns /config once it has started: after first boot the live
# copies win and nothing here is touched again. This script:
#   - copies the operator's bootstrap configuration.yaml / secrets.yaml from
#     /etc/quadlets/home-assistant into /config only if they are absent;
#   - creates the empty include targets configuration.yaml references
#     (automations.yaml / scenes.yaml / scripts.yaml) so Home Assistant does not
#     fall back to recovery mode on an otherwise-empty /config.
#
set -eu

SRC=/etc/quadlets/home-assistant
DST=/var/lib/virtiofs/data/home-assistant
HA_UID=10034
HA_GID=10000

install_if_absent() {
    if [ -f "$SRC/$1" ] && [ ! -e "$DST/$1" ]; then
        echo "Bootstrapping $DST/$1 from $SRC/$1"
        install -m "$2" -o "$HA_UID" -g "$HA_GID" "$SRC/$1" "$DST/$1"
    else
        echo "Keeping existing $DST/$1 (Home Assistant owns it) or no bootstrap provided"
    fi
}

stub_if_absent() {
    if [ ! -e "$DST/$1" ]; then
        echo "Creating empty $DST/$1"
        echo "$2" > "$DST/$1"
        chown "$HA_UID:$HA_GID" "$DST/$1"
    fi
}

install_if_absent configuration.yaml 0644
install_if_absent secrets.yaml 0600
stub_if_absent automations.yaml "[]"
stub_if_absent scenes.yaml "[]"
stub_if_absent scripts.yaml "{}"
