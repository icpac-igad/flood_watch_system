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

# Restore can leave country_code empty in control points, which breaks homepage country summaries.
# Recompute missing values from admin0 polygons so APIs stay stable after any DB refresh.
echo ""
echo "Backfilling multimodal country_code from admin0 geometry..."
docker exec "${CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
    WITH resolved AS (
        SELECT
            cp.point_id,
            CASE
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'ETH' THEN 'ET'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'KEN' THEN 'KE'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'UGA' THEN 'UG'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'SDN' THEN 'SD'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'SSD' THEN 'SS'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'TZA' THEN 'TZ'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'RWA' THEN 'RW'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'BDI' THEN 'BI'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'SOM' THEN 'SO'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'DJI' THEN 'DJ'
                WHEN UPPER(TRIM(COALESCE(a0.gid_0, ''))) = 'ERI' THEN 'ER'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'ethiopia' THEN 'ET'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'kenya' THEN 'KE'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'uganda' THEN 'UG'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'sudan' THEN 'SD'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'south sudan' THEN 'SS'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) IN ('tanzania', 'zanzibar') THEN 'TZ'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'rwanda' THEN 'RW'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'burundi' THEN 'BI'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'somalia' THEN 'SO'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'djibouti' THEN 'DJ'
                WHEN LOWER(TRIM(COALESCE(a0.country, ''))) = 'eritrea' THEN 'ER'
                ELSE NULL
            END AS country_code
        FROM gha.multimodal_control_points cp
        LEFT JOIN LATERAL (
            SELECT a0.gid_0, a0.country
            FROM gha.admin0 a0
            WHERE ST_Within(cp.geom, a0.geom)
            LIMIT 1
        ) a0 ON TRUE
    )
    UPDATE gha.multimodal_control_points cp
    SET country_code = resolved.country_code
    FROM resolved
    WHERE cp.point_id = resolved.point_id
      AND resolved.country_code IS NOT NULL
      AND COALESCE(NULLIF(UPPER(TRIM(cp.country_code)), ''), 'UN') = 'UN';
"

echo "Country-code coverage:"
docker exec "${CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
    SELECT
        COUNT(*) AS total_points,
        COUNT(*) FILTER (WHERE NULLIF(TRIM(country_code), '') IS NOT NULL) AS with_country_code,
        COUNT(*) FILTER (WHERE NULLIF(TRIM(country_code), '') IS NULL) AS missing_country_code
    FROM gha.multimodal_control_points;
"

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
echo "Done. Restart services: docker compose restart eafw_api eafw_tileserv eafw_cms"
