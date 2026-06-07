#!/bin/bash

set -Eeuo pipefail

for hook in /etc/quadlets/lego/renew-hooks.d/*.sh; do
    if [[ -x "$hook" ]]; then
        echo "Running renew hook: $hook"
        if ! "$hook"; then
            echo "Error: Renew hook failed: $hook" >&2
        fi
    else
        echo "Skipping non-executable hook: $hook"
    fi
done

rm -f /var/lib/quadlets/lego/certificates/*.renewed

exit 0