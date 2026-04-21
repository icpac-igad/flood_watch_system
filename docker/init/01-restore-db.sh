#!/usr/bin/env bash
# Restore the local database from backups/<DB_DUMP> if (and only if) the
# gha.multimodal_forecasts table is empty. Idempotent: running this a
# second time after a successful restore is a no-op.
#
# Env vars expected: PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE DB_DUMP

set -euo pipefail

: "${DB_DUMP:=/backups/staging_fresh.dump}"
MIN_ROWS=1000

echo "[restore-db] waiting for $PGHOST:$PGPORT"
until psql -c 'SELECT 1' >/dev/null 2>&1; do sleep 2; done

rows=$(psql -tAc "SELECT COUNT(*) FROM gha.multimodal_forecasts" 2>/dev/null || echo 0)
if [ "${rows:-0}" -ge "$MIN_ROWS" ]; then
  echo "[restore-db] DB already has $rows forecast rows — skipping restore"
  exit 0
fi

if [ ! -f "$DB_DUMP" ]; then
  echo "[restore-db] no dump at $DB_DUMP — skipping restore (init scripts will seed)"
  exit 0
fi

echo "[restore-db] restoring $DB_DUMP (forecast rows=${rows:-0})"
psql -v ON_ERROR_STOP=1 <<'SQL'
DROP SCHEMA IF EXISTS cms    CASCADE;
DROP SCHEMA IF EXISTS gha    CASCADE;
DROP SCHEMA IF EXISTS alerts CASCADE;
CREATE SCHEMA cms;
CREATE SCHEMA gha;
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA gha;
SQL
pg_restore --no-owner --role="$PGUSER" -d "$PGDATABASE" "$DB_DUMP" 2>&1 \
  | grep -vE 'already exists|warning: errors ignored' || true

rows=$(psql -tAc "SELECT COUNT(*) FROM gha.multimodal_forecasts" 2>/dev/null || echo 0)
echo "[restore-db] done — forecast rows now: $rows"
