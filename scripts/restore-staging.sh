#!/bin/bash
# Restore local database + media + static + raster data to staging
# Run on staging server: bash ~/eafw/scripts/restore-staging.sh
set -euo pipefail

RESTORE_DIR="${HOME}/eafw-restore"
EAFW_DIR="${HOME}/eafw"
COMPOSE_FILE="docker-compose.staging.yml"

# Staging DB credentials (from .env)
if [ -f "${EAFW_DIR}/.env" ]; then
  source <(grep -E '^(CMS_DB_USER|CMS_DB_NAME|CMS_DB_PASSWORD)=' "${EAFW_DIR}/.env")
fi
DB_USER="${CMS_DB_USER:-eafw_user}"
DB_NAME="${CMS_DB_NAME:-eafw_db}"

echo "========================================="
echo "  STAGING FULL RESTORE"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# Check files exist
DUMP_FILE=$(ls -t "${RESTORE_DIR}"/local_full_*.dump 2>/dev/null | head -1)
if [ -z "$DUMP_FILE" ]; then
  echo "FATAL: No dump file found in ${RESTORE_DIR}"
  exit 1
fi
echo "Dump file: ${DUMP_FILE} ($(du -h "$DUMP_FILE" | cut -f1))"

cd "${EAFW_DIR}"

# ── 1. BACKUP CURRENT STAGING DB (safety) ──
echo ""
echo "--- Step 1: Backup current staging DB ---"
mkdir -p ~/eafw-backups
SAFETY_BACKUP="${HOME}/eafw-backups/pre_restore_$(date +%Y%m%d_%H%M%S).dump"
if docker exec eafw-pgdb pg_isready -U "${DB_USER}" 2>/dev/null; then
  docker exec eafw-pgdb pg_dump -U "${DB_USER}" -Fc "${DB_NAME}" > "${SAFETY_BACKUP}" 2>/dev/null || true
  if [ -s "${SAFETY_BACKUP}" ]; then
    echo "Safety backup: ${SAFETY_BACKUP} ($(du -h "${SAFETY_BACKUP}" | cut -f1))"
  else
    echo "WARN: Safety backup empty/failed (may be fresh DB)"
    rm -f "${SAFETY_BACKUP}"
  fi
else
  echo "DB not running, skipping safety backup"
fi

# ── 2. STOP APPLICATION SERVICES (keep DB running) ──
echo ""
echo "--- Step 2: Stop app services ---"
docker compose -f "${COMPOSE_FILE}" --env-file .env stop eafw_cms eafw_api eafw_jobs eafw_mapviewer eafw_nginx 2>/dev/null || true
echo "App services stopped"

# ── 3. RESTORE DATABASE ──
echo ""
echo "--- Step 3: Restore database ---"
# Wait for DB to be ready
for i in $(seq 1 30); do
  docker exec eafw-pgdb pg_isready -U "${DB_USER}" 2>/dev/null && break
  sleep 2
done

# Drop and recreate DB
echo "Dropping existing database..."
docker exec eafw-pgdb psql -U "${DB_USER}" -d postgres -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();
" 2>/dev/null || true
docker exec eafw-pgdb dropdb -U "${DB_USER}" --if-exists "${DB_NAME}" 2>/dev/null || true
docker exec eafw-pgdb createdb -U "${DB_USER}" -O "${DB_USER}" "${DB_NAME}" 2>/dev/null

# Enable PostGIS
docker exec eafw-pgdb psql -U "${DB_USER}" -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS postgis;" 2>/dev/null

# Restore from dump
echo "Restoring from dump (this may take a few minutes)..."
# Copy dump into container, then restore
docker cp "${DUMP_FILE}" eafw-pgdb:/tmp/restore.dump
docker exec eafw-pgdb pg_restore -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-acl --jobs=4 /tmp/restore.dump 2>&1 | tail -5 || true
docker exec eafw-pgdb rm -f /tmp/restore.dump

# Reassign ownership
docker exec eafw-pgdb psql -U "${DB_USER}" -d "${DB_NAME}" -c "
  REASSIGN OWNED BY geomanager TO ${DB_USER};
" 2>/dev/null || true

echo "Database restored"

# Verify key tables
echo "Verifying data..."
docker exec eafw-pgdb psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
  SELECT 'control_points' as tbl, count(*) FROM gha.multimodal_control_points
  UNION ALL SELECT 'forecasts', count(*) FROM gha.multimodal_forecasts
  UNION ALL SELECT 'daily_alerts', count(*) FROM gha.daily_hmc_alerts
  UNION ALL SELECT 'admin0', count(*) FROM gha.admin0;
" 2>/dev/null

# ── 4. RESTORE MEDIA FILES ──
echo ""
echo "--- Step 4: Restore media files ---"
if [ -f "${RESTORE_DIR}/media.tar.gz" ]; then
  # Get the Docker volume mount path
  MEDIA_VOLUME=$(docker volume inspect eafw_media --format '{{.Mountpoint}}' 2>/dev/null || echo "")
  if [ -n "$MEDIA_VOLUME" ]; then
    echo "Extracting media to volume (${MEDIA_VOLUME})..."
    sudo tar xzf "${RESTORE_DIR}/media.tar.gz" -C "${MEDIA_VOLUME}" --strip-components=1
    echo "Media restored ($(du -sh "${MEDIA_VOLUME}" | cut -f1))"
  else
    echo "WARN: eafw_media volume not found, skipping"
  fi
else
  echo "No media.tar.gz found, skipping"
fi

# ── 5. RESTORE STATIC FILES ──
echo ""
echo "--- Step 5: Restore static files ---"
if [ -f "${RESTORE_DIR}/static.tar.gz" ]; then
  STATIC_VOLUME=$(docker volume inspect eafw_static --format '{{.Mountpoint}}' 2>/dev/null || echo "")
  if [ -n "$STATIC_VOLUME" ]; then
    echo "Extracting static to volume (${STATIC_VOLUME})..."
    sudo tar xzf "${RESTORE_DIR}/static.tar.gz" -C "${STATIC_VOLUME}" --strip-components=1
    echo "Static restored ($(du -sh "${STATIC_VOLUME}" | cut -f1))"
  else
    echo "WARN: eafw_static volume not found, skipping"
  fi
else
  echo "No static.tar.gz found, skipping"
fi

# ── 6. RESTORE RASTER DATA (COGs + Source) ──
echo ""
echo "--- Step 6: Restore raster data ---"
mkdir -p "${EAFW_DIR}/raster-data"

if [ -f "${RESTORE_DIR}/raster-cogs.tar.gz" ]; then
  echo "Extracting COGs..."
  tar xzf "${RESTORE_DIR}/raster-cogs.tar.gz" -C "${EAFW_DIR}"
  echo "COGs restored ($(du -sh "${EAFW_DIR}/raster-data/cogs" | cut -f1))"
fi

if [ -f "${RESTORE_DIR}/raster-source.tar.gz" ]; then
  echo "Extracting source rasters..."
  tar xzf "${RESTORE_DIR}/raster-source.tar.gz" -C "${EAFW_DIR}"
  echo "Source rasters restored ($(du -sh "${EAFW_DIR}/raster-data/source" | cut -f1))"
fi

# ── 7. RESTART ALL SERVICES ──
echo ""
echo "--- Step 7: Restart all services ---"
docker compose -f "${COMPOSE_FILE}" --env-file .env up -d
echo "Services starting..."

# Wait for DB + CMS
echo "Waiting for services to be ready..."
for i in $(seq 1 60); do
  docker exec eafw-pgdb pg_isready -U "${DB_USER}" 2>/dev/null && break
  sleep 3
done

# Run Django migrations (schema may differ between local and staging)
echo "Running Django migrations..."
sleep 10  # Give CMS time to start
for i in $(seq 1 12); do
  if docker exec eafw-cms /opt/venv/bin/python manage.py migrate --noinput 2>&1; then
    echo "Migrations completed"
    break
  fi
  echo "  Retry ${i}/12..."
  sleep 10
done

# Clear cache
docker exec eafw-cms /opt/venv/bin/python manage.py shell -c "from django.core.cache import caches; caches['default'].clear(); print('cache-cleared')" 2>&1 || true

# ── 8. HEALTH CHECK ──
echo ""
echo "========================================="
echo "  RESTORE COMPLETE"
echo "========================================="
docker ps --format "table {{.Names}}\t{{.Status}}" | grep eafw
echo ""
echo "Cleanup: rm -rf ${RESTORE_DIR}  (when satisfied)"
echo "Safety backup: ${SAFETY_BACKUP}"
echo "========================================="
