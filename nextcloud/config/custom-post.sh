#!/bin/sh

set -Eeuo pipefail

# Disable maintenance mode
echo "Disabling maintenance mode..."
php occ maintenance:mode --off

# Run database optimizations
echo "Adding missing database indices..."
php occ db:add-missing-indices || true

echo "Converting database columns to big int..."
php occ db:convert-filecache-bigint --no-interaction || true
