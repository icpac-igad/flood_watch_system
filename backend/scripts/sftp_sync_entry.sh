#!/bin/sh
set -e

# Ensure target dirs exist and are writable
mkdir -p /data/daily /data/inundation || true
chmod -R 777 /data/daily /data/inundation || true

exec python scripts/sftp_sync.py "$@"

