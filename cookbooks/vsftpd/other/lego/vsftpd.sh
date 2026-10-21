#!/bin/bash

set -Eeuo pipefail

# The vsftpd service copies the TLS certificates provided by lego when it starts (see ExecStartPre).
# "try-restart" does nothing if vsftpd is not running yet (first issuance at boot).
systemctl --no-block try-restart vsftpd.service
