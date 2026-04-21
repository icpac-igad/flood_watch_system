#!/usr/bin/env bash
# Apply every *.sql file in /db-init/ that isn't already baked into the
# initial postgis boot scripts. Only files explicitly listed here run —
# keep this list in sync as new migrations land.
#
# Runs post-restore so the new schema/functions live on top of the
# restored staging data.

set -euo pipefail

echo "[apply-migrations] waiting for $PGHOST:$PGPORT"
until psql -c 'SELECT 1' >/dev/null 2>&1; do sleep 2; done

# Add new migration filenames here in the order they should run.
MIGRATIONS=(
  /db-init/10-admin-overlay-function.sql
  /db-init/11-percentile-thresholds.sql
  /db-init/12-percentile-alert-levels.sql
  /db-init/13-forecast-tiles-percentile.sql
  /db-init/14-multimodal-points-alerts-percentile.sql
  /db-init/16-admin-dissolved-borders.sql
  /db-init/17-multimodal-points-per-point-date.sql
  /db-init/18-threshold-incremental-refresh.sql
  /db-init/19-multimodal-alerts-today.sql
  /db-init/20-point-admin-reenrich.sql
  /db-init/21-gauging-stations.sql
)

for sql in "${MIGRATIONS[@]}"; do
  if [ ! -f "$sql" ]; then
    echo "[apply-migrations] skip: $sql not found"
    continue
  fi
  echo "[apply-migrations] applying $(basename "$sql")"
  psql -q -v ON_ERROR_STOP=1 < "$sql"
done

echo "[apply-migrations] done"
