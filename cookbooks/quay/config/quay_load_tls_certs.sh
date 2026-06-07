#!/bin/bash

set -Eeuo pipefail

install -o 10026 -g 10000 -m 0600 $(ls /var/lib/quadlets/lego/certificates/*.crt | head -1) /run/quadlets/quay/tls/ssl.cert
install -o 10026 -g 10000 -m 0600 $(ls /var/lib/quadlets/lego/certificates/*.key | head -1) /run/quadlets/quay/tls/ssl.key
