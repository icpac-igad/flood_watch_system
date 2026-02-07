#!/bin/bash
# Backup database for staging deployment

set -e

BACKUP_DIR="./staging-deployment"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📊 Backing up database for staging..."

mkdir -p ${BACKUP_DIR}

# Backup database
docker exec eafw-cms-pgdb pg_dump -U geomanager -d geomanager_web \
  -F c -b -v -f /tmp/db_backup.dump

docker cp eafw-cms-pgdb:/tmp/db_backup.dump \
  ${BACKUP_DIR}/database_${TIMESTAMP}.dump

# Create latest symlink
ln -sf database_${TIMESTAMP}.dump ${BACKUP_DIR}/database_latest.dump

echo "✅ Database backed up to: ${BACKUP_DIR}/database_${TIMESTAMP}.dump"
echo ""
echo "Size: $(du -h ${BACKUP_DIR}/database_${TIMESTAMP}.dump | cut -f1)"
