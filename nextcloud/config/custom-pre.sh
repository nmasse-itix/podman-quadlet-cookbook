#!/bin/sh

set -Eeuo pipefail

# Enable maintenance mode
echo "Enabling maintenance mode..."
php occ maintenance:mode --on || true
