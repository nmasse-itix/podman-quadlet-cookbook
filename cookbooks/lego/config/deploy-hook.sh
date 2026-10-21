#!/bin/sh

# This hook runs inside the Lego container (busybox sh) after a certificate
# has been obtained or renewed. It flags the certificate as renewed so that
# lego-hooks.path triggers the renewal hooks on the host.
set -eu
touch "${LEGO_HOOK_CERT_PATH%.*}.renewed"
