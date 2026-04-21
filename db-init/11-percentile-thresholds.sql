-- ============================================================================
-- Percentile-based alert thresholds for multimodal control points.
--
-- Replaces the legacy global thresholds (warning=300, alarm=500, emergency=750)
-- with per-point percentiles computed from that point's own history:
--
--   level      label     rule
--   ---------  --------  -------------------------------------------
--   extreme    red       discharge >= p99
--   severe     orange    discharge >= p95 (but below p99)
--   moderate   yellow    discharge >= p90 (but below p95)
--   normal     grey      discharge <  p90
--
-- Thresholds are recomputed on demand via gha.refresh_point_alert_thresholds()
-- from a rolling window of historical daily_avg values.
-- ============================================================================

CREATE TABLE IF NOT EXISTS gha.point_alert_thresholds (
    point_id    INTEGER PRIMARY KEY REFERENCES gha.multimodal_control_points(point_id) ON DELETE CASCADE,
    p90         DOUBLE PRECISION,
    p95         DOUBLE PRECISION,
    p99         DOUBLE PRECISION,
    sample_size INTEGER,
    window_days INTEGER,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index to speed alert-level joins in tile / API queries
CREATE INDEX IF NOT EXISTS point_alert_thresholds_p90_idx ON gha.point_alert_thresholds (p90);


-- ----------------------------------------------------------------------------
-- Recompute per-point percentiles from gha.multimodal_forecasts.daily_avg
-- over the last <window_days> days. Non-destructive upsert.
-- Points with fewer than <min_samples> observations are skipped so we don't
-- produce noisy thresholds from sparse history.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION gha.refresh_point_alert_thresholds(
    window_days INTEGER DEFAULT 365,
    min_samples INTEGER DEFAULT 30
) RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    WITH per_point AS (
        SELECT
            point_id,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY daily_avg) AS p90,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY daily_avg) AS p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY daily_avg) AS p99,
            COUNT(*) AS sample_size
        FROM gha.multimodal_forecasts
        WHERE daily_avg IS NOT NULL
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


-- ----------------------------------------------------------------------------
-- Classify a discharge value for a given point into one of:
--   'extreme' | 'severe' | 'moderate' | 'normal'
--
-- Returns 'normal' if no thresholds are available for the point yet
-- (fail-open; callers can distinguish via a NULL threshold lookup if needed).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION gha.classify_alert_level_percentile(
    p_point_id INTEGER,
    p_discharge DOUBLE PRECISION
) RETURNS TEXT
LANGUAGE sql STABLE AS $$
    SELECT CASE
        WHEN p_discharge IS NULL THEN 'normal'
        WHEN t.p99 IS NOT NULL AND p_discharge >= t.p99 THEN 'extreme'
        WHEN t.p95 IS NOT NULL AND p_discharge >= t.p95 THEN 'severe'
        WHEN t.p90 IS NOT NULL AND p_discharge >= t.p90 THEN 'moderate'
        ELSE 'normal'
    END
    FROM (
        SELECT p90, p95, p99 FROM gha.point_alert_thresholds WHERE point_id = p_point_id
        UNION ALL SELECT NULL, NULL, NULL
        LIMIT 1
    ) t;
$$;


-- ----------------------------------------------------------------------------
-- Convenience: integer priority matching the existing scheme used in
-- forecast-provider-vector-tiles (1=extreme, 2=severe, 3=moderate, 4=normal)
-- so we can keep the clustering/top-of-stack logic identical.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION gha.alert_priority_percentile(p_level TEXT)
RETURNS INTEGER
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_level
        WHEN 'extreme'  THEN 1
        WHEN 'severe'   THEN 2
        WHEN 'moderate' THEN 3
        ELSE                 4
    END;
$$;
