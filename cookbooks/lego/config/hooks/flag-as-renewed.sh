#!/bin/sh
set -Eeuo pipefail
touch ${LEGO_CERT_PATH%.*}.renewed
