-- ============================================================================
-- Auto-update per-point percentile thresholds when new data lands.
--
-- Two ways to keep gha.point_alert_thresholds fresh:
--
--   A) gha.refresh_point_alert_thresholds_for(ids)
--      — incremental: called by the ingest job RIGHT AFTER it upserts
--        forecasts for a set of points. Only recomputes for those points.
--        Fast (<100ms for a handful of points).
--
--   B) gha.refresh_point_alert_thresholds()
--      — the existing full sweep. Still runs nightly (via the jobs scheduler)
--        as a safety net in case any incremental refresh was missed.
--
-- Both use the same window_days and min_samples defaults so thresholds
-- computed incrementally match the nightly-refreshed ones.
-- ============================================================================

CREATE OR REPLACE FUNCTION gha.refresh_point_alert_thresholds_for(
    point_ids   INTEGER[],
    window_days INTEGER DEFAULT 365,
    min_samples INTEGER DEFAULT 30
) RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    IF point_ids IS NULL OR cardinality(point_ids) = 0 THEN
        RETURN 0;
    END IF;

    WITH per_point AS (
        SELECT
            point_id,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY daily_avg) AS p90,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY daily_avg) AS p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY daily_avg) AS p99,
            COUNT(*) AS sample_size
        FROM gha.multimodal_forecasts
        WHERE daily_avg IS NOT NULL
          AND point_id = ANY(point_ids)
          AND forecast_date >= (CURRENT_DATE - (window_days || ' days')::INTERVAL)
        GROUP BY point_id
        HAVING COUNT(*) >= min_samples
    )
    INSERT INTO gha.point_alert_thresholds
        (point_id, p90, p95, p99, sample_size, window_days, computed_at)
    SELECT point_id, p90, p95, p99, sample_size, window_days, NOW()
    FROM per_point
    ON CONFLICT (point_id) DO UPDATE
        SET p90         = EXCLUDED.p90,
            p95         = EXCLUDED.p95,
            p99         = EXCLUDED.p99,
            sample_size = EXCLUDED.sample_size,
            window_days = EXCLUDED.window_days,
            computed_at = EXCLUDED.computed_at;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$;

COMMENT ON FUNCTION gha.refresh_point_alert_thresholds_for(INTEGER[], INTEGER, INTEGER) IS
    'Incremental threshold refresh — call from ingest jobs with the list of point_ids that just received new forecasts. Mirrors refresh_point_alert_thresholds() math for a subset.';
