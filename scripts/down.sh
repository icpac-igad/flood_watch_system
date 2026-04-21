#!/usr/bin/env bash
# Stop the EAFW stack. Volumes are preserved (local DB + media stay).
#
# Usage:
#   ./scripts/down.sh            # stop + remove containers, keep volumes
#   ./scripts/down.sh --keep     # just stop (containers remain, faster to restart)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ "${1:-}" = "--keep" ]; then
  echo "[down] stopping containers (keeping them)"
  docker-compose stop
else
  echo "[down] stopping and removing containers (keeping volumes)"
  docker-compose down
fi
