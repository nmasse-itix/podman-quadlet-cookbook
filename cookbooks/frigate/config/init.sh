#!/bin/sh
#
# Seed the Frigate configuration file on first boot.
#
# Frigate owns config.yml: the web interface writes the cameras, the masks and
# the zones back to it, and a new minor version migrates it in place. So this
# script only ever creates it when it is absent, and never touches it again.
#
set -eu

SRC=/etc/quadlets/frigate/config.yml
DST=/var/lib/virtiofs/data/frigate/config/config.yml

if [ -e "$DST" ]; then
    echo "Keeping existing $DST (Frigate owns it)"
    exit 0
fi

echo "Seeding $DST from $SRC"
install -m 0600 -o root -g root "$SRC" "$DST"
