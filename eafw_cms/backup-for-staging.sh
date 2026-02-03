#!/bin/bash
# Backup script for staging deployment
# Run this on your LOCAL/DEVELOPMENT environment

set -e  # Exit on error

BACKUP_DIR="/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/hazard_watch/geomanager-web/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="staging_backup_${TIMESTAMP}"

echo "🔄 Starting backup for staging deployment..."
echo "Backup directory: ${BACKUP_DIR}/${BACKUP_NAME}"

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# 1. Backup PostgreSQL database
echo "📊 Backing up database..."
docker exec eafw-pgdb pg_dump -U geomanager -d geomanager_web -F c -b -v \
  -f /tmp/db_backup.dump

docker cp eafw-pgdb:/tmp/db_backup.dump \
  "${BACKUP_DIR}/${BACKUP_NAME}/database.dump"

echo "✅ Database backed up: ${BACKUP_DIR}/${BACKUP_NAME}/database.dump"

# 2. Backup media files
echo "📁 Backing up media files..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/media.tar.gz" \
  -C /home/koros/IGAD-ICPAC/Projects/FloodWatch/code/hazard_watch/geomanager-web/data media

echo "✅ Media files backed up"

# 3. Backup static files
echo "📁 Backing up static files..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/static.tar.gz" \
  -C /home/koros/IGAD-ICPAC/Projects/FloodWatch/code/hazard_watch/geomanager-web/data static

echo "✅ Static files backed up"

# 4. Backup geomanager data
echo "📁 Backing up geomanager auto-ingest data..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/geomanager-data.tar.gz" \
  -C /home/koros/IGAD-ICPAC/Projects/FloodWatch/code/hazard_watch/geomanager-web/data geomanager-data

echo "✅ Geomanager data backed up"

# 5. Copy current .env file
echo "⚙️  Backing up .env configuration..."
cp /home/koros/IGAD-ICPAC/Projects/FloodWatch/code/hazard_watch/geomanager-web/.env \
  "${BACKUP_DIR}/${BACKUP_NAME}/env.development"

echo "✅ Environment configuration backed up"

# 6. Create backup info file
cat > "${BACKUP_DIR}/${BACKUP_NAME}/backup_info.txt" << EOF
Backup Information
==================
Date: $(date)
Hostname: $(hostname)
Database: geomanager_web
User: geomanager

Files included:
- database.dump (PostgreSQL custom format)
- media.tar.gz (uploaded media files)
- static.tar.gz (static files)
- geomanager-data.tar.gz (auto-ingest data)
- env.development (current .env file)

Restore instructions in restore-to-staging.sh
EOF

# 7. Create archive of entire backup
echo "📦 Creating final backup archive..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"

echo ""
echo "✅ =========================================="
echo "✅ BACKUP COMPLETED SUCCESSFULLY!"
echo "✅ =========================================="
echo ""
echo "Backup location: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Backup size: $(du -h ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz | cut -f1)"
echo ""
echo "To transfer to staging server:"
echo "  scp ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz user@staging-server:/path/to/destination/"
echo ""
echo "Next step: Run restore-to-staging.sh on the STAGING server"
echo ""
