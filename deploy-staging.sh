#!/bin/bash
# EAFW Staging Deployment Script
# Usage: ./deploy-staging.sh [--cms-only | --mapviewer-only | --all]

set -e

STAGING="staging"
REMOTE_DIR="~/flood_watch_system"
COMPOSE_DIR="$REMOTE_DIR/eafw_geomanager_web"

echo "=== EAFW Staging Deployment ==="
echo "$(date)"
echo ""

# 1. Pull latest code
echo ">> Pulling latest code..."
ssh $STAGING "cd $REMOTE_DIR && git pull origin eafw --ff-only"

MODE="${1:---all}"

# 2. Build CMS
if [[ "$MODE" == "--all" || "$MODE" == "--cms-only" ]]; then
  echo ""
  echo ">> Building CMS (with SSH forwarding for georeport)..."
  ssh -A $STAGING "cd $COMPOSE_DIR && DOCKER_BUILDKIT=1 docker compose build --ssh default geomanager_web"

  echo ">> Restarting CMS..."
  ssh $STAGING "cd $COMPOSE_DIR && docker compose up -d geomanager_web"

  echo ">> Running migrations..."
  sleep 10
  ssh $STAGING "docker exec eafw-cms /home/app/.venv/bin/python manage.py migrate"
fi

# 3. Build MapViewer
if [[ "$MODE" == "--all" || "$MODE" == "--mapviewer-only" ]]; then
  echo ""
  echo ">> Building MapViewer (this takes ~5 min)..."
  ssh $STAGING "cd $COMPOSE_DIR && docker compose build geomanager_mapviewer"

  echo ">> Restarting MapViewer..."
  ssh $STAGING "cd $COMPOSE_DIR && docker compose up -d geomanager_mapviewer"
fi

# 4. Build MapServer + MapCache (if configs changed)
if [[ "$MODE" == "--all" ]]; then
  echo ""
  echo ">> Building MapServer + MapCache..."
  ssh $STAGING "cd $COMPOSE_DIR && docker compose build geomanager_mapserver geomanager_mapcache"
  ssh $STAGING "cd $COMPOSE_DIR && docker compose up -d geomanager_mapserver geomanager_mapcache"
fi

# 5. Flush cache
echo ""
echo ">> Flushing cache..."
ssh $STAGING "docker exec eafw-memcached sh -c \"echo 'flush_all' | nc localhost 11211\""

# 6. Verify
echo ""
echo ">> Verifying..."
for page in "/" "/reports/" "/whca-project/" "/mapviewer/"; do
  code=$(ssh $STAGING "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9068${page}")
  echo "   ${page}: ${code}"
done

echo ""
echo "=== Deployment complete ==="
echo "$(date)"
