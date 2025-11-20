#!/bin/sh
set -e

# Use environment variables or defaults (proxy paths work with nginx config)
API_URL="${VITE_API_URL:-/api}"
FASTAPI_URL="${VITE_FASTAPI_URL:-/api/fast}"
# MapServer WMS URL - camptocamp/mapserver uses root endpoint
MAPSERVER_URL="${VITE_MAPSERVER_URL:-http://localhost:8095/}"
ALERTS_WMS_URL="${VITE_ALERTS_WMS_URL:-/wms}"
MAPCACHE_WMS_URL="${VITE_MAPCACHE_WMS_URL:-http://localhost:8096}"
MAPCACHE_TMS_URL="${VITE_MAPCACHE_TMS_URL:-http://localhost:8096/tms/1.0.0}"

echo "Configuring frontend with:"
echo "  API_URL: $API_URL"
echo "  FASTAPI_URL: $FASTAPI_URL"
echo "  MAPSERVER_URL: $MAPSERVER_URL"
echo "  ALERTS_WMS_URL: $ALERTS_WMS_URL"
echo "  MAPCACHE_WMS_URL: $MAPCACHE_WMS_URL"
echo "  MAPCACHE_TMS_URL: $MAPCACHE_TMS_URL"

# Replace placeholder values in all JS and HTML files
find /usr/share/nginx/html -type f \( -name "*.js" -o -name "*.html" \) -exec sed -i \
  -e "s|__VITE_API_URL__|${API_URL}|g" \
  -e "s|__VITE_FASTAPI_URL__|${FASTAPI_URL}|g" \
  -e "s|__VITE_MAPSERVER_URL__|${MAPSERVER_URL}|g" \
  -e "s|__VITE_ALERTS_WMS_URL__|${ALERTS_WMS_URL}|g" \
  -e "s|__VITE_MAPCACHE_WMS_URL__|${MAPCACHE_WMS_URL}|g" \
  -e "s|__VITE_MAPCACHE_TMS_URL__|${MAPCACHE_TMS_URL}|g" \
  {} +

echo "Environment variable replacement completed."
echo "Starting nginx as nginx user..."
exec nginx -g "daemon off;"
