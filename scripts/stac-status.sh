#!/usr/bin/env bash
set -euo pipefail

# STAC Status Overview for FloodWatch
# Usage: ./scripts/stac-status.sh

BASE_URL="${STAC_BASE_URL:-http://localhost:9068}"
STAC_API_PATH="${STAC_API_PATH:-/stac-browser/api}"
STAC_API_DIRECT="${STAC_API_DIRECT:-http://localhost:9070}"

echo "============================================"
echo " FloodWatch STAC Status"
echo "============================================"
echo ""

echo "Container Status:"
docker ps --filter "name=eafw-pgdb" --filter "name=eafw-stac" --filter "name=eafw-titiler" --filter "name=eafw-stac-browser" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  Docker not available"

echo ""
echo "Port Availability:"
for port in 9070 9071 9072 9073; do
    if curl -s --connect-timeout 2 "http://localhost:$port/" > /dev/null 2>&1; then
        echo "  :$port - OPEN"
    else
        echo "  :$port - CLOSED"
    fi
done

echo ""
echo "STAC Collections:"
curl -s "${STAC_API_DIRECT}/collections" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    colls = data.get('collections', [])
    print(f'  Total: {len(colls)}')
    for c in colls:
        print(f'  - {c[\"id\"]}: {c.get(\"title\", \"untitled\")}')
except: print('  Unable to fetch collections')
" 2>/dev/null || echo "  STAC API not available"

echo ""
echo "Gateway Endpoints:"
for path in "${STAC_API_PATH}/" "${STAC_API_PATH}/collections" "/stac-browser/" "/cog-tiles/healthz"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${path}" 2>/dev/null || echo "000")
    echo "  ${BASE_URL}${path} -> ${code}"
done

echo ""
echo "COG Data Directory:"
if [ -d "data/cogs" ]; then
    du -sh data/cogs/ 2>/dev/null || echo "  Not accessible"
    find data/cogs/ -name "*.tif" 2>/dev/null | wc -l | xargs echo "  COG files:"
else
    echo "  data/cogs/ not found (will be created as Docker volume)"
fi
