#!/bin/bash

set -Eeuo pipefail

install -o 10015 -g 10000 -m 0600 -t /run/quadlets/vsftpd/tls /var/lib/quadlets/lego/certificates/*.crt /var/lib/quadlets/lego/certificates/*.key
systemctl --no-block restart vsftpd.service
