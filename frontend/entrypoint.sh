#!/bin/sh
set -eu

TEMPLATE_PATH=/usr/share/nginx/html/env.template.js
OUTPUT_PATH=/usr/share/nginx/html/env-config.js

if [ -f "$TEMPLATE_PATH" ]; then
  echo "Rendering runtime environment config..."
envsubst '${PUBLIC_BACKEND_URL} ${PUBLIC_MAPSERVER_URL} ${PUBLIC_ALERTS_WMS_URL} ${PUBLIC_MAPCACHE_URL} ${PUBLIC_MAPCACHE_WMS_URL} ${PUBLIC_MAPCACHE_TMS_URL} ${PUBLIC_WMS_PROXY_BASE} ${PUBLIC_MAPCACHE_PROXY_BASE} ${PUBLIC_MAPSERVER_ASSETS_BASE} ${PUBLIC_MAPSERVER_MAP_FILE} ${PUBLIC_DEPLOY_ENV}' \
    < "$TEMPLATE_PATH" > "$OUTPUT_PATH"
else
  echo "Runtime env template not found at $TEMPLATE_PATH"
fi

exec "$@"
