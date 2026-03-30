#!/bin/sh
if [ -x /usr/local/bin/fastfetch ]; then
    declare -a FASTFETCH_OPTIONS=( -c /etc/quadlets/base/fastfetch.jsonc )
    if [ "$USER" == "root" ]; then
        FASTFETCH_OPTIONS+=( --custom-key-color dim_red --color-keys red --title-color-user red )
    else
        FASTFETCH_OPTIONS+=( --custom-key-color dim_blue --color-keys blue --title-color-user green )
    fi
    fastfetch "${FASTFETCH_OPTIONS[@]}"
    unset FASTFETCH_OPTIONS
fi
