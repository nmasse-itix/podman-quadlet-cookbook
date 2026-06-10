#!/bin/bash

set -Eeuo pipefail

ret=0
for tool in /etc/quadlets/base/install-tools.d/*.sh; do
    tool_name="$(basename "$tool" .sh)"
    echo "Installing $tool_name..."
    if ! "$tool"; then
        echo "Failed to install $tool_name!" >&2
        ret=1
    fi
done

exit $ret
