#!/usr/bin/env bash
# Nuke the local stack: stop everything, delete volumes (incl. the DB),
# then rebuild and start fresh. DESTRUCTIVE — use for a clean slate.
#
# Usage:
#   ./scripts/reset.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

cat <<'WARN'

[reset] this will DELETE:
  - every eafw container
  - every eafw volume (local DB, media, static, etc.)

press Ctrl+C within 5 seconds to abort.
WARN
sleep 5

echo "[reset] tearing down stack + volumes"
docker-compose down -v

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo "[reset] rebuilding images from scratch"
docker-compose build

echo "[reset] starting fresh stack (init service will restore + migrate)"
docker-compose up -d

echo "[reset] done — docker-compose ps:"
docker-compose ps
