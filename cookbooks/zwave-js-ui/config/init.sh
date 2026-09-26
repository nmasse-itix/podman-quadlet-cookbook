#!/bin/sh
#
# Seed the Z-Wave JS UI store on first boot.
#
# Z-Wave JS UI owns store/settings.json: every change made in the web interface
# is written back to it. So this script only ever creates it when it is absent,
# and never touches it again. What it seeds are the two settings the cookbook
# decides and that the external settings file cannot carry (Z-Wave JS UI only
# accepts `zwave.*` keys there):
#
#   - gateway.authEnabled, so the web interface asks for a password from the
#     very first boot rather than after an operator remembers to turn it on;
#   - mqtt.disabled, because a Z-Wave JS UI with no MQTT section at all builds no
#     MQTT client, and /health then reports 500 forever (the probe asks for both
#     halves of the gateway, and an absent client is indistinguishable from a
#     broken one).
#
# The keys of settings.json are merged with Z-Wave JS UI's own defaults at each
# start, so seeding a partial file loses nothing.
#
set -eu

SRC=/etc/quadlets/zwave-js-ui/initial-settings.json
DST=/var/lib/virtiofs/data/zwave-js-ui/settings.json
ZUI_UID=10035
ZUI_GID=10000

if [ -e "$DST" ]; then
    echo "Keeping existing $DST (Z-Wave JS UI owns it)"
    exit 0
fi

echo "Seeding $DST from $SRC"
install -m 0600 -o "$ZUI_UID" -g "$ZUI_GID" "$SRC" "$DST"
