#!/bin/bash

set -Eeuo pipefail

# In development mode, it is not possible to get a certificate from Let's Encrypt,
# so we just create a self-signed certificate for localhost, so that other services can still use it.
# The certificate is named "default", like the certificate declared in the example lego.yaml.
CERT_DIR=/var/lib/quadlets/lego/certificates
CERT_NAME=default

if [ -f "$CERT_DIR/$CERT_NAME.crt" ] && [ -f "$CERT_DIR/$CERT_NAME.key" ] && openssl x509 -in "$CERT_DIR/$CERT_NAME.crt" -noout -checkend $((30 * 86400)) &>/dev/null; then
    echo "Self-signed certificate is still valid for more than 30 days."
    exit 0
fi

echo "Generating self-signed certificate for localhost..."
install -d -m 0700 -o 10023 -g 10000 "$CERT_DIR"
(
    umask 0077
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout "$CERT_DIR/$CERT_NAME.key" -out "$CERT_DIR/$CERT_NAME.crt" -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost"
)
chown 10023:10000 "$CERT_DIR/$CERT_NAME.key" "$CERT_DIR/$CERT_NAME.crt"

echo "Flagging certificate as renewed..."
install -m 0600 -o 10023 -g 10000 /dev/null "$CERT_DIR/$CERT_NAME.renewed"
