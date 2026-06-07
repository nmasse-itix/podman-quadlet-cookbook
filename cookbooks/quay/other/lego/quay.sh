#!/bin/bash

set -Eeuo pipefail

/etc/quadlets/quay/quay_load_tls_certs.sh
systemctl --no-block restart quay-app.service
