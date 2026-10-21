#!/bin/bash

set -Eeuo pipefail

install -o 10030 -g 10000 -m 0600 -t /run/quadlets/smtprelay/tls /var/lib/quadlets/lego/certificates/*.crt /var/lib/quadlets/lego/certificates/*.key
# "try-restart" does nothing if smtprelay is not running yet (first issuance at boot).
systemctl --no-block try-restart smtprelay.service
