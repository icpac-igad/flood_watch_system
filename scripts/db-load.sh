#!/usr/bin/env bash
# EAFW Database Restore
# Usage: ./scripts/db-restore.sh <dump_file>
# Example: ./scripts/db-restore.sh backups/eafw_db_staging_20260207.dump
set -euo pipefail

DUMP_FILE="${1:?Usage: $0 <dump_file>}"
CONTAINER="${DB_CNTR_NAME:-eafw-pgdb}"
DB_USER="${CMS_DB_USER:-geomanager}"
DB_NAME="${CMS_DB_NAME:-geomanager_web}"

if [ ! -f "${DUMP_FILE}" ]; then
    echo "ERROR: File not found: ${DUMP_FILE}"
    exit 1
fi

SIZE=$(stat -c%s "${DUMP_FILE}" 2>/dev/null || stat -f%z "${DUMP_FILE}" 2>/dev/null)
SIZE_MB=$((SIZE / 1024 / 1024))

echo "=== EAFW DB Restore ==="
echo "File:      ${DUMP_FILE} (${SIZE_MB} MB)"
echo "Container: ${CONTAINER}"
echo "Database:  ${DB_NAME}"
echo ""
echo "WARNING: This will drop and recreate all schemas (gha, cms, wrf, etc.)"
read -p "Continue? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Create a backup first
echo ""
echo "Creating safety backup before restore..."
SAFETY_DUMP="eafw_db_pre_restore_$(date +%Y%m%d_%H%M%S).dump"
docker exec "${CONTAINER}" pg_dump \
    -U "${DB_USER}" -d "${DB_NAME}" -Fc \
    --no-owner --no-privileges \
    -f "/backups/${SAFETY_DUMP}" 2>/dev/null || echo "  (skipped - DB may be empty)"

# Copy dump into container
echo "Copying dump to container..."
docker cp "${DUMP_FILE}" "${CONTAINER}:/tmp/restore.dump"

# Drop existing schemas
echo "Dropping existing schemas..."
docker exec "${CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
    DROP SCHEMA IF EXISTS gha CASCADE;
    DROP SCHEMA IF EXISTS cms CASCADE;
    DROP SCHEMA IF EXISTS wrf CASCADE;
    DROP SCHEMA IF EXISTS climate CASCADE;
    DROP SCHEMA IF EXISTS ogr_system_tables CASCADE;
    DROP SCHEMA IF EXISTS tiger_data CASCADE;
    DROP MATERIALIZED VIEW IF EXISTS public.multimodal_points CASCADE;
" 2>&1 | grep -v "^NOTICE:" || true

# Restore
echo "Restoring from ${DUMP_FILE}..."
docker exec "${CONTAINER}" pg_restore \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-owner \
    --no-privileges \
    /tmp/restore.dump 2>&1 | tail -5

# Cleanup
docker exec "${CONTAINER}" rm -f /tmp/restore.dump

# Verify
echo ""
echo "Verifying restore..."
docker exec "${CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
    SELECT schemaname, count(*) as tables
    FROM pg_tables
    WHERE schemaname IN ('gha','cms','wrf','climate')
    GROUP BY schemaname ORDER BY schemaname;
"

echo ""
echo "Done. Restart services: docker compose -f docker-compose.local.yml restart eafw_api eafw_tileserv eafw_cms"
