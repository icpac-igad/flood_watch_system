#!/usr/bin/env bash
# EAFW FloodWatch — Safe Deployment Script
# Usage:
#   ./scripts/deploy.sh cms             # deploy CMS only
#   ./scripts/deploy.sh mapviewer       # deploy mapviewer only
#   ./scripts/deploy.sh cms mapviewer   # deploy multiple services
#   ./scripts/deploy.sh --full          # deploy all app services
#   ./scripts/deploy.sh --init          # first-time setup (includes DB init)
#
# Environment variables (set by CI or manually):
#   DEPLOY_SHA    — git SHA to pull images by tag (e.g. abc123)
#   DEPLOY_TAG    — version tag (e.g. v1.0.0), defaults to "latest"
#
# This script NEVER touches the database or pgbouncer unless --init is passed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${EAFW_BACKUP_DIR:-$HOME/eafw-backups}"
REGISTRY="${REGISTRY:-ghcr.io/icpac-igad}"

# ── Colour helpers ──────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[EAFW]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Service name mapping ───────────────────────────────────────
# Maps friendly names to compose service names and image names
declare -A SVC_MAP=(
  [cms]=geomanager_web
  [mapviewer]=geomanager_mapviewer
  [mapserver]=geomanager_mapserver
  [mapcache]=geomanager_mapcache
  [jobs]=geomanager_jobs
  [nginx]=geomanager_nginx
  [tileserv]=geomanager_tileserv
  [memcached]=geomanager_memcached
)

declare -A IMG_MAP=(
  [cms]=eafw-cms
  [mapviewer]=eafw-mapviewer
  [mapserver]=eafw-mapserver
  [mapcache]=eafw-mapcache
  [jobs]=eafw-jobs
)

# ── Parse arguments ─────────────────────────────────────────────
SERVICES=()
FRIENDLY_NAMES=()
FULL=false
INIT=false
SKIP_BACKUP=false

for arg in "$@"; do
  case "$arg" in
    --full)        FULL=true ;;
    --init)        INIT=true ;;
    --skip-backup) SKIP_BACKUP=true ;;
    cms|mapviewer|mapserver|mapcache|jobs|nginx|tileserv|memcached)
      FRIENDLY_NAMES+=("$arg")
      SERVICES+=("${SVC_MAP[$arg]}")
      ;;
    *)  error "Unknown argument: $arg"; exit 1 ;;
  esac
done

if $FULL; then
  FRIENDLY_NAMES=(cms mapviewer mapserver mapcache jobs nginx tileserv memcached)
  SERVICES=(geomanager_web geomanager_mapviewer geomanager_mapserver geomanager_mapcache geomanager_jobs geomanager_nginx geomanager_tileserv geomanager_memcached)
fi

if [ ${#SERVICES[@]} -eq 0 ]; then
  error "No services specified. Use: ./deploy.sh cms mapviewer  or  ./deploy.sh --full"
  exit 1
fi

cd "$REPO_DIR"

# ── Validate .env exists ────────────────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    warn ".env not found — copying from .env.example"
    cp .env.example .env
  else
    error "No .env or .env.example found"; exit 1
  fi
fi

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-eafw}"

info "========================================="
info "  EAFW Deployment v1.0"
info "  $(date '+%Y-%m-%d %H:%M:%S')"
info "  Services: ${FRIENDLY_NAMES[*]}"
info "  SHA: ${DEPLOY_SHA:-local}"
info "========================================="

# ── First-time init: start DB + wait ────────────────────────────
if $INIT; then
  info "First-time init: starting database..."
  docker compose up -d geomanager_db
  info "Waiting for database to initialize..."
  for i in $(seq 1 120); do
    if docker exec eafw-pgdb pg_isready -U "${CMS_DB_USER:-geomanager}" 2>/dev/null; then
      info "Database ready after $((i*5))s"
      break
    fi
    [ $i -eq 120 ] && { error "Database failed to start"; docker logs eafw-pgdb --tail 20; exit 1; }
    sleep 5
  done
  docker compose up -d geomanager_pgbouncer
  sleep 3
fi

# ── Backup DB (if running) ──────────────────────────────────────
if ! $SKIP_BACKUP; then
  DB_STATUS=$(docker inspect --format='{{.State.Status}}' eafw-pgdb 2>/dev/null || echo "none")
  if [ "$DB_STATUS" = "running" ]; then
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/pre_deploy_$(date +%Y%m%d_%H%M%S).dump"
    info "Backing up database..."
    DB_USER=$(grep -E '^CMS_DB_USER=' .env | cut -d= -f2 | tr -d '"' || echo "geomanager")
    DB_NAME=$(grep -E '^CMS_DB_NAME=' .env | cut -d= -f2 | tr -d '"' || echo "geomanager_web")
    if docker exec eafw-pgdb pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null; then
      info "Backup: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
    else
      warn "Backup failed — continuing"; rm -f "$BACKUP_FILE"
    fi
    ls -t "$BACKUP_DIR"/pre_deploy_*.dump 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
  fi
fi

# ── Ensure infrastructure is running ────────────────────────────
DB_CNTR=$(grep -E '^DB_CNTR_NAME=' .env | cut -d= -f2 | tr -d '"' || echo "eafw-pgdb")
PGB_CNTR=$(grep -E '^PGBOUNCER_CNTR_NAME=' .env | cut -d= -f2 | tr -d '"' || echo "eafw-pgbouncer")

for pair in "geomanager_db:$DB_CNTR" "geomanager_pgbouncer:$PGB_CNTR"; do
  svc="${pair%%:*}"; cntr="${pair##*:}"
  STATUS=$(docker inspect --format='{{.State.Status}}' "$cntr" 2>/dev/null || echo "none")
  if [ "$STATUS" = "running" ]; then
    info "Infrastructure OK: $cntr"
  elif [ "$STATUS" != "none" ]; then
    info "Starting: $cntr"; docker start "$cntr"
  else
    info "Creating: $svc"; docker compose up -d "$svc"
  fi
done

# ── Adopt orphaned containers ───────────────────────────────────
PROTECTED="$DB_CNTR $PGB_CNTR"
for svc in "${SERVICES[@]}"; do
  EXPECTED=$(docker compose config --format json 2>/dev/null | python3 -c "
import sys,json; c=json.load(sys.stdin); print(c.get('services',{}).get('$svc',{}).get('container_name',''))" 2>/dev/null || echo "")
  [ -z "$EXPECTED" ] && continue
  echo "$PROTECTED" | grep -qw "$EXPECTED" && continue
  EXISTING=$(docker inspect --format='{{.Id}}' "$EXPECTED" 2>/dev/null || echo "")
  MANAGED=$(docker compose ps -q "$svc" 2>/dev/null || echo "")
  if [ -n "$EXISTING" ] && [ "$EXISTING" != "$MANAGED" ]; then
    info "Removing orphaned: $EXPECTED"
    docker rm -f "$EXPECTED" 2>/dev/null || true
  fi
done

# ── Pull images ─────────────────────────────────────────────────
# If DEPLOY_SHA is set (from CI), pull by SHA tag — guaranteed fresh.
# Then retag so docker-compose uses the correct image.
if [ -n "${DEPLOY_SHA:-}" ]; then
  info "Pulling images by SHA: ${DEPLOY_SHA:0:12}"
  for name in "${FRIENDLY_NAMES[@]}"; do
    img="${IMG_MAP[$name]:-}"
    [ -z "$img" ] && continue  # no image for this service (nginx, tileserv, memcached)
    SHA_TAG="${REGISTRY}/${img}:${DEPLOY_SHA}"
    LATEST_TAG="${REGISTRY}/${img}:latest"
    info "  Pulling $img:${DEPLOY_SHA:0:12}..."
    if docker pull "$SHA_TAG" 2>&1; then
      docker tag "$SHA_TAG" "$LATEST_TAG"
      info "  Tagged $img:latest"
    else
      warn "  Failed to pull $SHA_TAG — using existing image"
    fi
  done
else
  # Manual deploy — pull :latest for services that have custom images
  info "Pulling latest images..."
  for name in "${FRIENDLY_NAMES[@]}"; do
    img="${IMG_MAP[$name]:-}"
    [ -z "$img" ] && continue
    docker pull "${REGISTRY}/${img}:latest" 2>&1 || warn "Failed to pull $img"
  done
fi

# ── Restart services ────────────────────────────────────────────
info "Restarting: ${FRIENDLY_NAMES[*]}"
docker compose up -d --no-deps --force-recreate "${SERVICES[@]}"

# ── Run migrations ──────────────────────────────────────────────
if printf '%s\n' "${SERVICES[@]}" | grep -q "geomanager_web"; then
  info "Waiting for CMS..."
  for i in $(seq 1 60); do
    if docker exec eafw-cms test -f /home/app/manage.py 2>/dev/null; then
      info "Running migrations..."
      docker exec eafw-cms /home/app/.venv/bin/python manage.py migrate --noinput 2>&1 || warn "Migration warnings"
      docker exec eafw-cms /home/app/.venv/bin/python manage.py collectstatic --clear --no-input 2>&1 || true
      break
    fi
    [ $i -eq 60 ] && { error "CMS did not start"; docker logs eafw-cms --tail 20; }
    sleep 5
  done
fi

# ── Reload nginx ────────────────────────────────────────────────
if printf '%s\n' "${SERVICES[@]}" | grep -q "geomanager_nginx"; then
  docker exec eafw-nginx nginx -s reload 2>&1 || docker restart eafw-nginx 2>/dev/null || true
fi

# ── Cleanup ─────────────────────────────────────────────────────
docker image prune -f 2>/dev/null || true

# ── Summary ─────────────────────────────────────────────────────
info ""
info "========================================="
info "  DEPLOYMENT COMPLETE"
info "========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" --filter "name=eafw-"
info "========================================="
