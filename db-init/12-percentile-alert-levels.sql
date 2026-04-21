-- ============================================================================
-- Percentile-based alert levels for the forecast tile functions.
--
-- Replaces the legacy global-threshold classification
--   daily_avg >= 750 -> 'emergency'
--   daily_avg >= 500 -> 'alarm'
--   daily_avg >= 300 -> 'warning'
--   else             -> 'normal'
-- with per-point percentiles computed from that point's own history:
--   daily_avg >= p99 -> 'extreme'
--   daily_avg >= p95 -> 'severe'
--   daily_avg >= p90 -> 'moderate'
--   else             -> 'normal'
--
-- Points without computed percentiles (e.g. too few history samples) fall
-- back to the old global thresholds so nothing breaks mid-rollout.
--
-- Requires 11-percentile-thresholds.sql to have been applied.
-- ============================================================================

-- ── Helpers ────────────────────────────────────────────────────────────────

-- Classify a discharge value for a point. Prefers per-point percentiles;
-- falls back to legacy global thresholds when no per-point data exists.
CREATE OR REPLACE FUNCTION gha.classify_alert(
    p_point_id INTEGER,
    p_value    DOUBLE PRECISION
) RETURNS TEXT
LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN p_value IS NULL                                  THEN 'normal'
        -- Per-point percentile thresholds
        WHEN t.p99 IS NOT NULL AND p_value >= t.p99           THEN 'extreme'
        WHEN t.p95 IS NOT NULL AND p_value >= t.p95           THEN 'severe'
        WHEN t.p90 IS NOT NULL AND p_value >= t.p90           THEN 'moderate'
        WHEN t.point_id IS NOT NULL                           THEN 'normal'
        -- Fallback: no per-point thresholds for this point yet
        WHEN p_value >= 750                                   THEN 'extreme'
        WHEN p_value >= 500                                   THEN 'severe'
        WHEN p_value >= 300                                   THEN 'moderate'
        ELSE                                                       'normal'
    END
    FROM (SELECT 1) dummy
    LEFT JOIN gha.point_alert_thresholds t ON t.point_id = p_point_id;
$$;

-- Numeric priority for sorting / stacking (extreme=4 .. normal=1).
-- Matches the order used by the frontend for cluster colouring.
CREATE OR REPLACE FUNCTION gha.alert_priority(p_level TEXT)
RETURNS INTEGER
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE p_level
        WHEN 'extreme'  THEN 4
        WHEN 'severe'   THEN 3
        WHEN 'moderate' THEN 2
        ELSE                 1
    END;
$$;

-- Translate legacy filter-key values to a SQL predicate against alert_level.
-- Keeps the existing query-string contract (`?filter=emergency` etc.) working
-- while we migrate callers to the new names (`extreme`, `severe`, `moderate`).
CREATE OR REPLACE FUNCTION gha.alert_filter_matches(p_level TEXT, p_filter TEXT)
RETURNS BOOLEAN
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE lower(coalesce(p_filter, 'all'))
        WHEN 'all'       THEN TRUE
        WHEN 'active'    THEN p_level <> 'normal'
        WHEN 'moderate'  THEN p_level IN ('moderate', 'severe', 'extreme')
        WHEN 'warning'   THEN p_level IN ('moderate', 'severe', 'extreme') -- legacy alias
        WHEN 'severe'    THEN p_level IN ('severe', 'extreme')
        WHEN 'alarm'     THEN p_level IN ('severe', 'extreme')             -- legacy alias
        WHEN 'extreme'   THEN p_level = 'extreme'
        WHEN 'emergency' THEN p_level = 'extreme'                          -- legacy alias
        ELSE                  TRUE
    END;
$$;

COMMENT ON FUNCTION gha.classify_alert(INTEGER, DOUBLE PRECISION) IS
    'Returns extreme|severe|moderate|normal for a discharge at a given point, using per-point p90/p95/p99 with fallback to legacy global thresholds.';
