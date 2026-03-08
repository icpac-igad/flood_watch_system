#!/bin/bash

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/opt/venv/bin/python}"
WATCHMEDO_BIN="${WATCHMEDO_BIN:-/opt/venv/bin/watchmedo}"
RUN_MIGRATIONS_ON_STARTUP="${RUN_MIGRATIONS_ON_STARTUP:-true}"
RUN_COLLECTSTATIC_ON_STARTUP="${RUN_COLLECTSTATIC_ON_STARTUP:-true}"

is_truthy() {
  case "${1,,}" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

if is_truthy "$RUN_MIGRATIONS_ON_STARTUP"; then
  echo "Running Django migrations..."
  "$PYTHON_BIN" manage.py migrate --noinput
else
  echo "Skipping migrations (RUN_MIGRATIONS_ON_STARTUP=$RUN_MIGRATIONS_ON_STARTUP)."
fi

if is_truthy "$RUN_COLLECTSTATIC_ON_STARTUP"; then
  echo "Collecting static files..."
  "$PYTHON_BIN" manage.py collectstatic --clear --no-input
else
  echo "Skipping collectstatic (RUN_COLLECTSTATIC_ON_STARTUP=$RUN_COLLECTSTATIC_ON_STARTUP)."
fi

# ensure environment-variables are available for cronjob
printenv | grep -v "no_proxy" >>/etc/environment || true

# ensure cron is running
service cron start
service cron status

# create geomanager auto-ingest data dir
export GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=${GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR:-/geomanager/data}
mkdir -p "$GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR"

# start command to watch for new files in the geomanager auto-ingest data dir
if [ -x "$WATCHMEDO_BIN" ]; then
  "$WATCHMEDO_BIN" shell-command --patterns="*.nc;*.tif" --ignore-directories --recursive \
    --command="$PYTHON_BIN manage.py ingest_geomanager_raster \"\${watch_event_type}\" \"\${watch_src_path}\" --dst \"\${watch_dest_path}\" --overwrite" \
    "$GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR" &
else
  echo "WARN: watchmedo not found at $WATCHMEDO_BIN, skipping auto-ingest file watcher."
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi
