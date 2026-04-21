#!/usr/bin/env bash
# Recompute per-point percentile alert thresholds (p90/p95/p99) from the
# rolling window of multimodal_forecasts history. Safe to re-run any
# time — the function uses an INSERT … ON CONFLICT UPDATE.
#
# Tune via env:
#   THRESHOLD_WINDOW_DAYS (default 365)
#   THRESHOLD_MIN_SAMPLES (default 30)

set -euo pipefail

: "${THRESHOLD_WINDOW_DAYS:=365}"
: "${THRESHOLD_MIN_SAMPLES:=30}"

echo "[compute-thresholds] waiting for $PGHOST:$PGPORT"
until psql -c 'SELECT 1' >/dev/null 2>&1; do sleep 2; done

rows=$(psql -tAc "SELECT COUNT(*) FROM gha.multimodal_forecasts" 2>/dev/null || echo 0)
if [ "${rows:-0}" -lt 100 ]; then
  echo "[compute-thresholds] only ${rows:-0} forecast rows — skipping (need history first)"
  exit 0
fi

echo "[compute-thresholds] recomputing (window=${THRESHOLD_WINDOW_DAYS}d, min_samples=${THRESHOLD_MIN_SAMPLES})"
psql -v ON_ERROR_STOP=1 -c "SELECT gha.refresh_point_alert_thresholds(${THRESHOLD_WINDOW_DAYS}, ${THRESHOLD_MIN_SAMPLES}) AS updated_points;"

echo "[compute-thresholds] done"
