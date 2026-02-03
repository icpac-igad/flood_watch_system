#!/bin/bash

# migrate db
python manage.py migrate --noinput

# collect static files
python manage.py collectstatic --clear --no-input

# ensure environment-variables are available for cronjob
printenv | grep -v "no_proxy" >>/etc/environment

# ensure cron is running
service cron start
service cron status

# create geomanager auto-ingest data dir
export GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=${GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR:-/geomanager/data}
mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR

# start command to watch for new files in the geomanager auto-ingest data dir
watchmedo shell-command --patterns="*.nc;*.tif" --ignore-directories --recursive \
  --command='python manage.py ingest_geomanager_raster "${watch_event_type}" "${watch_src_path}" --dst "${watch_dest_path}" --overwrite' \
  $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR &

exec "$@"
