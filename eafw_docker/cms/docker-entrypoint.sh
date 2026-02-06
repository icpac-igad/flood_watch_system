#!/bin/bash

set -u

PYTHON_BIN="${PYTHON_BIN:-/opt/venv/bin/python}"
WATCHMEDO_BIN="${WATCHMEDO_BIN:-/opt/venv/bin/watchmedo}"

# migrate db
if ! "$PYTHON_BIN" manage.py migrate --noinput; then
  echo "WARN: migrate failed; continuing startup."
fi

# collect static files
if ! "$PYTHON_BIN" manage.py collectstatic --clear --no-input; then
  echo "WARN: collectstatic failed; continuing startup."
fi

# ensure environment-variables are available for cronjob
printenv | grep -v "no_proxy" >>/etc/environment

# ensure cron is running
service cron start
service cron status

# create geomanager auto-ingest data dir
export GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=${GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR:-/geomanager/data}
mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR

# start command to watch for new files in the geomanager auto-ingest data dir
if [ -x "$WATCHMEDO_BIN" ]; then
  "$WATCHMEDO_BIN" shell-command --patterns="*.nc;*.tif" --ignore-directories --recursive \
    --command="$PYTHON_BIN manage.py ingest_geomanager_raster \"\${watch_event_type}\" \"\${watch_src_path}\" --dst \"\${watch_dest_path}\" --overwrite" \
    "$GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR" &
else
  echo "WARN: watchmedo not found at $WATCHMEDO_BIN, skipping auto-ingest file watcher."
fi

exec "$@"
