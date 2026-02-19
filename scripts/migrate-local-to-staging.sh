#!/bin/bash
# ============================================================================
# migrate-local-to-staging.sh
#
# One-time data migration from local EAFW instance to staging server.
# Transfers: PostgreSQL dump, media files, and mapfiles (with rasters).
#
# Usage:
#   ./scripts/migrate-local-to-staging.sh [options]
#
# Options:
#   --dump-only       Only create local dumps (no transfer)
#   --transfer-only   Only transfer existing dumps to staging (no local dump)
#   --restore-only    Only restore on staging (assumes files already transferred)
#   --all             Full pipeline: dump → transfer → restore (default)
#   --skip-db         Skip database dump/restore
#   --skip-media      Skip media files
#   --skip-mapfiles   Skip mapfiles/rasters
#   --staging-host    Staging SSH host (default: hkoros@41.139.151.242)
#   --staging-dir     Staging project dir (default: ~/eafw)
#   --dry-run         Show what would be done without executing
# ============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DUMP_DIR="${HOME}/eafw-migration-dumps"

STAGING_HOST="${STAGING_HOST:-hkoros@41.139.151.242}"
STAGING_DIR="${STAGING_DIR:-~/eafw}"

# Local Docker container/compose names
LOCAL_COMPOSE="${PROJECT_DIR}/docker-compose.yml"
LOCAL_DB_CONTAINER="eafw-pgdb"
LOCAL_DB_USER="geomanager"
LOCAL_DB_NAME="geomanager_web"

# Staging container names
STAGING_DB_CONTAINER="eafw-pgdb"
STAGING_CMS_CONTAINER="eafw-cms"

# What to migrate
DO_DB=true
DO_MEDIA=true
DO_MAPFILES=true

# Pipeline steps
DO_DUMP=true
DO_TRANSFER=true
DO_RESTORE=true
DRY_RUN=false

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --dump-only)     DO_TRANSFER=false; DO_RESTORE=false; shift ;;
    --transfer-only) DO_DUMP=false; DO_RESTORE=false; shift ;;
    --restore-only)  DO_DUMP=false; DO_TRANSFER=false; shift ;;
    --all)           shift ;;
    --skip-db)       DO_DB=false; shift ;;
    --skip-media)    DO_MEDIA=false; shift ;;
    --skip-mapfiles) DO_MAPFILES=false; shift ;;
    --staging-host)  STAGING_HOST="$2"; shift 2 ;;
    --staging-dir)   STAGING_DIR="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=true; shift ;;
    *)               echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo -e "\033[1;34m[$(date +%H:%M:%S)]\033[0m $*"; }
ok()   { echo -e "\033[1;32m  ✓\033[0m $*"; }
warn() { echo -e "\033[1;33m  ⚠\033[0m $*"; }
err()  { echo -e "\033[1;31m  ✗\033[0m $*" >&2; }

run() {
  if $DRY_RUN; then
    echo "  [dry-run] $*"
  else
    "$@"
  fi
}

human_size() {
  local size=$1
  if [[ $size -gt 1073741824 ]]; then
    echo "$(( size / 1073741824 ))G"
  elif [[ $size -gt 1048576 ]]; then
    echo "$(( size / 1048576 ))M"
  elif [[ $size -gt 1024 ]]; then
    echo "$(( size / 1024 ))K"
  else
    echo "${size}B"
  fi
}

# ── Pre-flight checks ───────────────────────────────────────────────────────
log "Pre-flight checks..."

if $DO_DUMP; then
  if ! docker ps --format '{{.Names}}' | grep -q "^${LOCAL_DB_CONTAINER}$"; then
    err "Local DB container '${LOCAL_DB_CONTAINER}' is not running"
    err "Start it with: docker compose up -d eafw_db"
    exit 1
  fi
  ok "Local DB container running"
fi

if $DO_TRANSFER; then
  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$STAGING_HOST" true 2>/dev/null; then
    err "Cannot SSH to staging: $STAGING_HOST"
    err "Check SSH key/config or try: ssh $STAGING_HOST"
    exit 1
  fi
  ok "SSH to staging OK"
fi

mkdir -p "$DUMP_DIR"

# ── STEP 1: Local dumps ─────────────────────────────────────────────────────
if $DO_DUMP; then
  log "Step 1: Creating local dumps..."

  # Database dump
  if $DO_DB; then
    log "  Dumping PostgreSQL database..."
    DB_DUMP="${DUMP_DIR}/eafw_db.dump"
    run docker exec "$LOCAL_DB_CONTAINER" \
      pg_dump -U "$LOCAL_DB_USER" -Fc --no-owner --no-privileges "$LOCAL_DB_NAME" \
      > "$DB_DUMP"
    if [[ -f "$DB_DUMP" ]]; then
      ok "DB dump: $(human_size "$(stat -c%s "$DB_DUMP" 2>/dev/null || stat -f%z "$DB_DUMP")")"
    fi
  fi

  # Media files
  if $DO_MEDIA; then
    log "  Archiving media files..."
    MEDIA_TAR="${DUMP_DIR}/eafw_media.tar.gz"
    # Extract media from Docker volume via CMS container
    if docker ps --format '{{.Names}}' | grep -q "^eafw-cms$"; then
      run docker exec eafw-cms tar czf - -C /opt/eafw_cms/media . > "$MEDIA_TAR"
    elif [[ -d "${PROJECT_DIR}/data/media" ]]; then
      run tar czf "$MEDIA_TAR" -C "${PROJECT_DIR}/data/media" .
    else
      warn "No media source found (container or ./data/media/)"
    fi
    if [[ -f "$MEDIA_TAR" ]]; then
      ok "Media archive: $(human_size "$(stat -c%s "$MEDIA_TAR" 2>/dev/null || stat -f%z "$MEDIA_TAR")")"
    fi
  fi

  # Mapfiles + rasters
  if $DO_MAPFILES; then
    log "  Archiving mapfiles and rasters..."
    MAPFILES_TAR="${DUMP_DIR}/eafw_mapfiles.tar.gz"
    MAPFILES_DIR="${PROJECT_DIR}/data/mapfiles"
    if [[ -d "$MAPFILES_DIR" ]]; then
      run tar czf "$MAPFILES_TAR" -C "$MAPFILES_DIR" .
      if [[ -f "$MAPFILES_TAR" ]]; then
        ok "Mapfiles archive: $(human_size "$(stat -c%s "$MAPFILES_TAR" 2>/dev/null || stat -f%z "$MAPFILES_TAR")")"
      fi
    else
      warn "No mapfiles directory at $MAPFILES_DIR"
    fi
  fi

  log "Dumps complete. Files in: $DUMP_DIR"
  ls -lh "$DUMP_DIR"/
fi

# ── STEP 2: Transfer to staging ──────────────────────────────────────────────
if $DO_TRANSFER; then
  log "Step 2: Transferring to staging ($STAGING_HOST)..."

  REMOTE_DUMP_DIR="\${HOME}/eafw-migration-dumps"

  # Create staging dump directory
  run ssh "$STAGING_HOST" "mkdir -p ~/eafw-migration-dumps"

  if $DO_DB && [[ -f "${DUMP_DIR}/eafw_db.dump" ]]; then
    log "  Transferring DB dump..."
    run rsync -avz --progress "${DUMP_DIR}/eafw_db.dump" \
      "${STAGING_HOST}:~/eafw-migration-dumps/"
    ok "DB dump transferred"
  fi

  if $DO_MEDIA && [[ -f "${DUMP_DIR}/eafw_media.tar.gz" ]]; then
    log "  Transferring media archive..."
    run rsync -avz --progress "${DUMP_DIR}/eafw_media.tar.gz" \
      "${STAGING_HOST}:~/eafw-migration-dumps/"
    ok "Media transferred"
  fi

  if $DO_MAPFILES && [[ -f "${DUMP_DIR}/eafw_mapfiles.tar.gz" ]]; then
    log "  Transferring mapfiles archive..."
    run rsync -avz --progress "${DUMP_DIR}/eafw_mapfiles.tar.gz" \
      "${STAGING_HOST}:~/eafw-migration-dumps/"
    ok "Mapfiles transferred"
  fi

  log "Transfer complete."
fi

# ── STEP 3: Restore on staging ───────────────────────────────────────────────
if $DO_RESTORE; then
  log "Step 3: Restoring on staging..."

  REMOTE_DUMP_DIR="\${HOME}/eafw-migration-dumps"

  # Database restore
  if $DO_DB; then
    log "  Restoring database..."
    run ssh "$STAGING_HOST" bash <<REMOTE_DB
set -euo pipefail
cd ${STAGING_DIR}

# Source staging env for DB credentials
export \$(grep -E '^(CMS_DB_USER|CMS_DB_NAME|CMS_DB_PASSWORD)=' .env | xargs)

echo "  Stopping services that use the DB..."
docker stop ${STAGING_CMS_CONTAINER} eafw-api eafw-jobs eafw-tileserv 2>/dev/null || true
sleep 5

echo "  Dropping and recreating database..."
docker exec ${STAGING_DB_CONTAINER} psql -U \${CMS_DB_USER} -d postgres -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '\${CMS_DB_NAME}' AND pid <> pg_backend_pid();
" 2>/dev/null || true
docker exec ${STAGING_DB_CONTAINER} dropdb -U \${CMS_DB_USER} --if-exists \${CMS_DB_NAME}
docker exec ${STAGING_DB_CONTAINER} createdb -U \${CMS_DB_USER} \${CMS_DB_NAME}

echo "  Restoring from dump..."
docker exec -i ${STAGING_DB_CONTAINER} pg_restore -U \${CMS_DB_USER} -d \${CMS_DB_NAME} --no-owner --no-privileges --verbose < ${REMOTE_DUMP_DIR}/eafw_db.dump 2>&1 | tail -5

echo "  Running init scripts for roles/extensions..."
for f in eafw_docker/db-init/00-init-roles.sql eafw_docker/db-init/04-mapserver-alerts-compat.sql; do
  if [[ -f "\$f" ]]; then
    docker exec -i ${STAGING_DB_CONTAINER} psql -U \${CMS_DB_USER} -d \${CMS_DB_NAME} < "\$f" 2>&1 | tail -3
  fi
done

echo "  Restarting services..."
docker start ${STAGING_CMS_CONTAINER} eafw-api eafw-jobs eafw-tileserv
sleep 10

echo "  Running Django migrations (in case of schema drift)..."
docker exec ${STAGING_CMS_CONTAINER} python manage.py migrate --noinput 2>&1 | tail -5

echo "  DB restore complete."
REMOTE_DB
    ok "Database restored"
  fi

  # Media restore
  if $DO_MEDIA; then
    log "  Restoring media files..."
    run ssh "$STAGING_HOST" bash <<REMOTE_MEDIA
set -euo pipefail
cd ${STAGING_DIR}

echo "  Extracting media into CMS container volume..."
docker exec -i ${STAGING_CMS_CONTAINER} bash -c 'mkdir -p /opt/eafw_cms/media && tar xzf - -C /opt/eafw_cms/media' < ${REMOTE_DUMP_DIR}/eafw_media.tar.gz

echo "  Setting permissions..."
docker exec ${STAGING_CMS_CONTAINER} chown -R nobody:nogroup /opt/eafw_cms/media 2>/dev/null || true

echo "  Collecting static files..."
docker exec ${STAGING_CMS_CONTAINER} python manage.py collectstatic --noinput 2>&1 | tail -3

echo "  Media restore complete."
REMOTE_MEDIA
    ok "Media restored"
  fi

  # Mapfiles restore
  if $DO_MAPFILES; then
    log "  Restoring mapfiles and rasters..."
    run ssh "$STAGING_HOST" bash <<REMOTE_MAPFILES
set -euo pipefail
cd ${STAGING_DIR}

echo "  Extracting mapfiles..."
mkdir -p data/mapfiles
tar xzf ${REMOTE_DUMP_DIR}/eafw_mapfiles.tar.gz -C data/mapfiles/

echo "  Restarting map services..."
docker restart eafw-mapserver eafw-mapcache 2>/dev/null || true
sleep 5

echo "  Mapfiles restore complete."
REMOTE_MAPFILES
    ok "Mapfiles restored"
  fi

  # Final health check
  log "  Running health checks..."
  run ssh "$STAGING_HOST" bash <<REMOTE_HEALTH
set -euo pipefail
cd ${STAGING_DIR}

echo ""
echo "========================================="
echo "  POST-MIGRATION HEALTH CHECK"
echo "========================================="

# Container status
echo ""
echo "Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep eafw | sort

# DB check
echo ""
echo "Database:"
docker exec ${STAGING_DB_CONTAINER} psql -U eafw_user -d eafw_db -c "
  SELECT
    (SELECT count(*) FROM gha.multimodal_control_points) as control_points,
    (SELECT count(*) FROM gha.multimodal_forecasts) as forecasts;
" 2>/dev/null || echo "  DB query failed"

# HTTP check
echo ""
echo "HTTP endpoints:"
for path in "/" "/api/v1/" "/health"; do
  status=\$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:9068\${path}" 2>/dev/null || echo "ERR")
  echo "  http://127.0.0.1:9068\${path} → \${status}"
done

echo ""
echo "========================================="
echo "  Migration complete!"
echo "========================================="
REMOTE_HEALTH

  log "All done!"
fi
