#!/bin/bash
set -e

# migrate db
python manage.py migrate --noinput

# Clear the static dir BEFORE collectstatic instead of letting --clear
# do it. Django 4.2 ManifestStaticFilesStorage races between --clear and
# the post-process pass: a deleted hashed file gets re-targeted by the
# group-id chown step and the entrypoint dies with FileNotFoundError on
# files like admin/js/vendor/select2/i18n/<lang>.<hash>.js. Doing the
# wipe out-of-band makes the two phases sequential, not concurrent.
STATIC_ROOT_DIR="${STATIC_ROOT:-/home/app/static}"
if [ -d "$STATIC_ROOT_DIR" ]; then
  find "$STATIC_ROOT_DIR" -mindepth 1 -delete 2>/dev/null || true
fi
mkdir -p "$STATIC_ROOT_DIR"
python manage.py collectstatic --no-input

# Compile gettext translations (.po -> .mo) so LANGUAGE_CODE-prefixed URLs
# can load translations on request. Idempotent: skipped for locales that
# are already up to date.
python manage.py compilemessages 2>&1 | tail -5 || true

# ensure environment-variables are available for cronjob
printenv | grep -v "no_proxy" >>/etc/environment

# ensure cron is running
service cron start
service cron status

# create geomanager auto-ingest data dir
export GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR=${GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR:-/geomanager/data}
mkdir -p $GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR

exec "$@"
