#!/usr/bin/env bash
# Build (if needed) and start the whole EAFW stack.
# Re-runnable: no-op when everything's already up and images are current.
#
# Usage:
#   ./scripts/up.sh            # build if missing + start
#   ./scripts/up.sh --build    # force rebuild all images
#
# Config lives in ./.env (copy from .env.sample first time).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[ -f .env ] || { echo "[up] .env missing — copy from .env.sample first" >&2; exit 1; }
[ -f docker-compose.yml ] || { echo "[up] docker-compose.yml missing" >&2; exit 1; }

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

if [ "${1:-}" = "--build" ]; then
  echo "[up] forcing rebuild of all custom images"
  docker-compose build
fi

echo "[up] starting stack"
docker-compose up -d

echo "[up] services:"
docker-compose ps

cat <<EOT

visit:
  CMS:        http://127.0.0.1:9068
  CMS admin:  http://127.0.0.1:9068/cms-admin/
  MapViewer:  http://127.0.0.1:9068/mapviewer/
  Tileserv:   http://127.0.0.1:9068/pg/tileserv/index.json

logs:   docker-compose logs -f <service>     (e.g. geomanager_web)
psql:   docker-compose exec geomanager_db psql -U \$CMS_DB_USER -d \$CMS_DB_NAME
EOT
