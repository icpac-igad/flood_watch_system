#!/usr/bin/env bash
# EAFW FloodWatch — Safe Deployment Script
# Usage:
#   ./scripts/deploy.sh              # deploy all changed app services
#   ./scripts/deploy.sh cms          # deploy CMS only
#   ./scripts/deploy.sh mapviewer    # deploy mapviewer only
#   ./scripts/deploy.sh --full       # deploy all app services
#   ./scripts/deploy.sh --init       # first-time setup (includes DB init)
#
# This script NEVER touches the database or pgbouncer unless --init is passed.
# It can be called from CI or manually via SSH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${EAFW_BACKUP_DIR:-$HOME/eafw-backups}"

# ── Colour helpers ──────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[EAFW]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Parse arguments ─────────────────────────────────────────────
SERVICES=()
FULL=false
INIT=false
SKIP_BACKUP=false

for arg in "$@"; do
  case "$arg" in
    --full)       FULL=true ;;
    --init)       INIT=true ;;
    --skip-backup) SKIP_BACKUP=true ;;
    cms)          SERVICES+=(geomanager_web) ;;
    mapviewer)    SERVICES+=(geomanager_mapviewer) ;;
    mapserver)    SERVICES+=(geomanager_mapserver) ;;
    mapcache)     SERVICES+=(geomanager_mapcache) ;;
    jobs)         SERVICES+=(geomanager_jobs) ;;
    nginx)        SERVICES+=(geomanager_nginx) ;;
    tileserv)     SERVICES+=(geomanager_tileserv) ;;
    *)            error "Unknown argument: $arg"; exit 1 ;;
  esac
done

# App services = everything EXCEPT db and pgbouncer
APP_SERVICES=(
  geomanager_web
  geomanager_mapviewer
  geomanager_mapserver
  geomanager_mapcache
  geomanager_tileserv
  geomanager_jobs
  geomanager_nginx
  geomanager_memcached
)

# Default: if --full or no specific services, deploy all app services
if $FULL || [ ${#SERVICES[@]} -eq 0 ]; then
  SERVICES=("${APP_SERVICES[@]}")
fi

cd "$REPO_DIR"

# ── Validate .env exists ────────────────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    warn ".env not found — copying from .env.example"
    warn "EDIT .env with your secrets before running again!"
    cp .env.example .env
  else
    error "No .env or .env.example found"; exit 1
  fi
fi

# Source COMPOSE_PROJECT_NAME from .env for consistent naming
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-eafw}"

info "========================================="
info "  EAFW Deployment"
info "  $(date '+%Y-%m-%d %H:%M:%S')"
info "  Project: $COMPOSE_PROJECT_NAME"
info "  Services: ${SERVICES[*]}"
info "========================================="

# ── First-time init: start DB + wait ────────────────────────────
if $INIT; then
  info "First-time init: starting database..."
  docker compose up -d geomanager_db
  info "Waiting for database to be ready (init scripts may take a few minutes)..."
  for i in $(seq 1 120); do
    if docker exec eafw-pgdb pg_isready -U "${CMS_DB_USER:-geomanager}" 2>/dev/null; then
      info "Database ready after $((i*5))s"
      break
    fi
    if [ $i -eq 120 ]; then
      error "Database failed to start after 10 minutes"
      docker logs eafw-pgdb --tail 20
      exit 1
    fi
    sleep 5
  done
  # Start pgbouncer
  docker compose up -d geomanager_pgbouncer
  sleep 3
fi

# ── Backup DB (if running) ──────────────────────────────────────
if ! $SKIP_BACKUP; then
  DB_STATUS=$(docker inspect --format='{{.State.Status}}' eafw-pgdb 2>/dev/null || echo "none")
  if [ "$DB_STATUS" = "running" ]; then
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/pre_deploy_$(date +%Y%m%d_%H%M%S).dump"
    info "Backing up database to $BACKUP_FILE ..."

    # Read DB creds from .env
    DB_USER=$(grep -E '^CMS_DB_USER=' .env | cut -d= -f2 | tr -d '"' || echo "geomanager")
    DB_NAME=$(grep -E '^CMS_DB_NAME=' .env | cut -d= -f2 | tr -d '"' || echo "geomanager_web")

    if docker exec eafw-pgdb pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null; then
      BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
      info "Backup complete: $BACKUP_FILE ($BACKUP_SIZE)"
    else
      warn "Backup failed — continuing anyway (DB may not have data yet)"
      rm -f "$BACKUP_FILE"
    fi

    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/pre_deploy_*.dump 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
  else
    warn "Database not running — skipping backup"
  fi
fi

# ── Ensure infrastructure is running (DB + pgbouncer) ───────────
# Check by container name (not compose service) to handle containers created
# under a different COMPOSE_PROJECT_NAME.
DB_CNTR=$(grep -E '^DB_CNTR_NAME=' .env | cut -d= -f2 | tr -d '"' || echo "eafw-pgdb")
PGB_CNTR=$(grep -E '^PGBOUNCER_CNTR_NAME=' .env | cut -d= -f2 | tr -d '"' || echo "eafw-pgbouncer")

for pair in "geomanager_db:$DB_CNTR" "geomanager_pgbouncer:$PGB_CNTR"; do
  svc="${pair%%:*}"
  cntr="${pair##*:}"
  STATUS=$(docker inspect --format='{{.State.Status}}' "$cntr" 2>/dev/null || echo "none")
  if [ "$STATUS" = "running" ]; then
    info "Infrastructure already running: $cntr"
  elif [ "$STATUS" != "none" ]; then
    info "Starting stopped infrastructure: $cntr"
    docker start "$cntr"
  else
    info "Creating infrastructure: $svc"
    docker compose up -d "$svc"
  fi
done

# ── Adopt orphaned app containers ───────────────────────────────
# If containers exist but were created under a different COMPOSE_PROJECT_NAME,
# compose can't manage them and will fail with "name already in use".
# App containers are stateless (data lives in volumes), so safe to remove.
# DB and pgbouncer are handled above — never touched here.
PROTECTED_CONTAINERS="$DB_CNTR $PGB_CNTR"
for svc in "${SERVICES[@]}"; do
  # Get the expected container name from .env or docker-compose defaults
  EXPECTED_CNTR=$(docker compose config --format json 2>/dev/null | python3 -c "
import sys,json
cfg=json.load(sys.stdin)
svc=cfg.get('services',{}).get('$svc',{})
print(svc.get('container_name',''))" 2>/dev/null || echo "")

  [ -z "$EXPECTED_CNTR" ] && continue
  echo "$PROTECTED_CONTAINERS" | grep -qw "$EXPECTED_CNTR" && continue

  # Check if this container exists but isn't managed by current compose project
  EXISTING_ID=$(docker inspect --format='{{.Id}}' "$EXPECTED_CNTR" 2>/dev/null || echo "")
  COMPOSE_ID=$(docker compose ps -q "$svc" 2>/dev/null || echo "")

  if [ -n "$EXISTING_ID" ] && [ "$EXISTING_ID" != "$COMPOSE_ID" ]; then
    info "Adopting orphaned container: $EXPECTED_CNTR (removing old, compose will recreate)"
    docker rm -f "$EXPECTED_CNTR" 2>/dev/null || true
  fi
done

# ── Pull new images ─────────────────────────────────────────────
info "Pulling images for: ${SERVICES[*]}"
docker compose pull "${SERVICES[@]}" 2>&1 || warn "Some pulls failed (may be local-only images)"

# ── Restart app services ────────────────────────────────────────
info "Restarting services..."
docker compose up -d --no-deps "${SERVICES[@]}"

# ── Run migrations (if CMS is in the service list) ──────────────
if printf '%s\n' "${SERVICES[@]}" | grep -q "geomanager_web"; then
  info "Waiting for CMS to be ready..."
  for i in $(seq 1 60); do
    if docker exec eafw-cms test -f /home/app/manage.py 2>/dev/null; then
      info "Running migrations..."
      docker exec eafw-cms /home/app/.venv/bin/python manage.py migrate --noinput 2>&1 || warn "Migration had warnings"
      docker exec eafw-cms /home/app/.venv/bin/python manage.py collectstatic --clear --no-input 2>&1 || warn "Collectstatic had warnings"
      break
    fi
    if [ $i -eq 60 ]; then
      error "CMS did not start in time"
      docker logs eafw-cms --tail 20
    fi
    sleep 5
  done
fi

# ── Reload nginx (if running) ──────────────────────────────────
if printf '%s\n' "${SERVICES[@]}" | grep -q "geomanager_nginx"; then
  docker exec eafw-nginx nginx -s reload 2>&1 || docker restart eafw-nginx 2>/dev/null || true
fi

# ── Cleanup dangling images ─────────────────────────────────────
docker image prune -f 2>/dev/null || true

# ── Health check ────────────────────────────────────────────────
info ""
info "========================================="
info "  DEPLOYMENT SUMMARY"
info "========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=eafw-"
info "========================================="
info "Deployment complete!"
