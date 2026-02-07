#!/usr/bin/env bash
# EAFW Database Backup
# Usage: ./scripts/db-backup.sh [local|staging]
# Backups are stored in the eafw_backups Docker volume (/backups inside the container)
# and optionally copied to ./backups/ on the host.
set -euo pipefail

ENV="${1:-local}"
CONTAINER="${DB_CNTR_NAME:-eafw-pgdb}"
DB_USER="${CMS_DB_USER:-geomanager}"
DB_NAME="${CMS_DB_NAME:-geomanager_web}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_NAME="eafw_db_${ENV}_${TIMESTAMP}.dump"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"

echo "=== EAFW DB Backup ==="
echo "Environment: ${ENV}"
echo "Container:   ${CONTAINER}"
echo "Database:    ${DB_NAME}"
echo "Backup:      ${DUMP_NAME}"
echo ""

# Run pg_dump inside the container, output to /backups volume
docker exec "${CONTAINER}" pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -Fc \
    --no-owner \
    --no-privileges \
    -f "/backups/${DUMP_NAME}"

# Verify the dump
SIZE=$(docker exec "${CONTAINER}" stat -c%s "/backups/${DUMP_NAME}" 2>/dev/null || echo 0)
SIZE_MB=$((SIZE / 1024 / 1024))

if [ "${SIZE}" -lt 1000 ]; then
    echo "ERROR: Backup file is too small (${SIZE} bytes). Something went wrong."
    exit 1
fi

echo "Backup created: ${DUMP_NAME} (${SIZE_MB} MB)"

# Copy to host backups/ directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST_BACKUPS="${SCRIPT_DIR}/../backups"
mkdir -p "${HOST_BACKUPS}"
docker cp "${CONTAINER}:/backups/${DUMP_NAME}" "${HOST_BACKUPS}/${DUMP_NAME}"
echo "Copied to: backups/${DUMP_NAME}"

# Prune old backups in volume (keep last N days)
echo ""
echo "Pruning backups older than ${KEEP_DAYS} days..."
docker exec "${CONTAINER}" find /backups -name "eafw_db_*.dump" -mtime +"${KEEP_DAYS}" -delete 2>/dev/null || true

# List current backups
echo ""
echo "Current backups in volume:"
docker exec "${CONTAINER}" ls -lh /backups/eafw_db_*.dump 2>/dev/null || echo "  (none)"
echo ""
echo "Done."
