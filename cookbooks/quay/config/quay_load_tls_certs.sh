#!/bin/bash

set -Eeuo pipefail

if ls /var/lib/quadlets/lego/certificates/*.crt &> /dev/null; then
    echo "Lego-issued certificates found, loading them for Quay..."
    install -o 10026 -g 10000 -m 0600 $(ls /var/lib/quadlets/lego/certificates/*.crt | head -1) /etc/quadlets/quay/app/ssl.cert
    install -o 10026 -g 10000 -m 0600 $(ls /var/lib/quadlets/lego/certificates/*.key | head -1) /etc/quadlets/quay/app/ssl.key
elif [ ! -f /etc/quadlets/quay/app/ssl.cert ] && [ ! -f /etc/quadlets/quay/app/ssl.key ]; then
    echo "No Lego-issued certificates found, generating self-signed certificates for Quay..."
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/quadlets/quay/app/ssl.key -out /etc/quadlets/quay/app/ssl.cert -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost"
    chown 10026:10000 /etc/quadlets/quay/app/ssl.{key,cert}
    chmod 0600 /etc/quadlets/quay/app/ssl.{key,cert}
fi
