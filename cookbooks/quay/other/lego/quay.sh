#!/bin/bash

set -Eeuo pipefail

# On the first issuance, quay-app has not loaded any certificate yet: it is not
# running (its ExecStartPre loads the certificates) and will pick up the new
# certificate by itself when it starts. Restarting it would be useless.
if [ ! -s /run/quadlets/quay/tls/ssl.cert ]; then
    echo "No TLS certificate loaded in Quay yet, skipping the restart of quay-app."
    exit 0
fi

/etc/quadlets/quay/quay_load_tls_certs.sh
systemctl --no-block restart quay-app.service
