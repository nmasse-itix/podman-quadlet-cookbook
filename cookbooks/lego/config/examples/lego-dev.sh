#!/bin/bash

set -Eeuo pipefail

# In development mode, it is not possible to get a certificate from Let's Encrypt, so we just create a self-signed certificate for localhost, so that other services can still use it.
mkdir -p /var/lib/quadlets/lego/certificates
if [ -f /var/lib/quadlets/lego/certificates/localhost.crt ] && [ -f /var/lib/quadlets/lego/certificates/localhost.key ]; then
    renewal="yes"
else
    renewal="no"
fi

echo "Generating self-signed certificate for localhost..."
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /var/lib/quadlets/lego/certificates/localhost.key -out /var/lib/quadlets/lego/certificates/localhost.crt -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost"

if [[ "$renewal" == "yes" ]]; then
    echo "Flagging certificate as renewed..."
    touch /var/lib/quadlets/lego/certificates/localhost.renewed
fi
