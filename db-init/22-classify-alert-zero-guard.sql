-- ============================================================================
-- Zero-value guard for gha.classify_alert and gha.classify_alert_level_percentile
--
-- Bug: points whose daily_avg=0 AND whose per-point p99=0 were classifying
-- as 'extreme' because `0 >= 0` is true. These are zero-discharge points
-- with all-zero threshold rows (stale/minor basins) that should stay normal.
--
-- Fix: treat zero/negative input values as 'normal' up front, and require
-- each percentile threshold to be strictly > 0 before comparing.
-- ============================================================================

CREATE OR REPLACE FUNCTION gha.classify_alert(p_point_id integer, p_value double precision)
RETURNS text LANGUAGE sql STABLE PARALLEL SAFE AS $function$
    SELECT CASE
        WHEN p_value IS NULL OR p_value <= 0 THEN 'normal'
        WHEN t.p99 IS NOT NULL AND t.p99 > 0 AND p_value >= t.p99 THEN 'extreme'
        WHEN t.p95 IS NOT NULL AND t.p95 > 0 AND p_value >= t.p95 THEN 'severe'
        WHEN t.p90 IS NOT NULL AND t.p90 > 0 AND p_value >= t.p90 THEN 'moderate'
        WHEN t.point_id IS NOT NULL THEN 'normal'
        WHEN p_value >= 750 THEN 'extreme'
        WHEN p_value >= 500 THEN 'severe'
        WHEN p_value >= 300 THEN 'moderate'
        ELSE 'normal'
    END
    FROM (SELECT 1) dummy
    LEFT JOIN gha.point_alert_thresholds t ON t.point_id = p_point_id;
$function$;

CREATE OR REPLACE FUNCTION gha.classify_alert_level_percentile(p_point_id integer, p_discharge double precision)
RETURNS text LANGUAGE sql STABLE AS $function$
    SELECT CASE
        WHEN p_discharge IS NULL OR p_discharge <= 0 THEN 'normal'
        WHEN t.p99 IS NOT NULL AND t.p99 > 0 AND p_discharge >= t.p99 THEN 'extreme'
        WHEN t.p95 IS NOT NULL AND t.p95 > 0 AND p_discharge >= t.p95 THEN 'severe'
        WHEN t.p90 IS NOT NULL AND t.p90 > 0 AND p_discharge >= t.p90 THEN 'moderate'
        ELSE 'normal'
    END
    FROM (
        SELECT p90, p95, p99 FROM gha.point_alert_thresholds WHERE point_id = p_point_id
        UNION ALL SELECT NULL, NULL, NULL
        LIMIT 1
    ) t;
$function$;
