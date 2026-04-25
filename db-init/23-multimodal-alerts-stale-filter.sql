-- ============================================================================
-- Tile function for multimodal points with two resilience improvements:
--
-- 1. Safe date parsing: frontend race conditions occasionally pass the literal
--    template string '{{time}}' before the selected-time state is populated.
--    Swallow that in a BEGIN/EXCEPTION block so the tile returns data instead
--    of 500. Invalid date = "use latest run per point".
--
-- 2. Filter stale forecasting points: a point with no forecast within 14 days
--    is excluded so the chart popup never renders empty. Gauging stations
--    are always shown (no forecast chart path).
-- ============================================================================

CREATE OR REPLACE FUNCTION gha.multimodal_points_alerts(z integer, x integer, y integer, date text DEFAULT ''::text, project_countries text DEFAULT ''::text, scope text DEFAULT ''::text)
 RETURNS bytea
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    tile_env  geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    query_date date;
    mvt bytea;
    pc_arr text[];
    use_whca boolean := (scope IS NOT NULL AND lower(trim(scope)) = 'whca');
BEGIN
    IF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        pc_arr := string_to_array(project_countries, ',');
    END IF;
    -- Safe date parse: swallow garbage (e.g. literal '{{time}}' from frontend
    -- race conditions) and fall back to 'use latest run per point'.
    IF date IS NOT NULL AND date <> '' THEN
        BEGIN
            query_date := date::date;
        EXCEPTION WHEN OTHERS THEN
            query_date := NULL;
        END;
    END IF;

    SELECT ST_AsMVT(tile, 'gha.multimodal_points_alerts', 4096, 'mvt_geom')
    INTO mvt
    FROM (
        SELECT
            cp.point_id, cp.country_code, cp.whca_selected, cp.station_type,
            cp.zone, cp.admin_name,
            COALESCE(f.daily_avg, 0) AS daily_avg,
            gha.classify_alert(cp.point_id, f.daily_avg) AS alert_level,
            gha.alert_priority(gha.classify_alert(cp.point_id, f.daily_avg)) AS alert_priority,
            ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
        FROM gha.multimodal_control_points cp
        LEFT JOIN LATERAL (
            WITH pt AS (
                SELECT MAX(data_date) AS dd
                FROM gha.multimodal_forecasts
                WHERE point_id = cp.point_id
                  AND (query_date IS NULL OR data_date = query_date)
            )
            SELECT daily_avg
            FROM (
                SELECT x.daily_avg,
                       (x.forecast_date <= CURRENT_DATE) AS is_past_or_today,
                       x.forecast_date
                FROM gha.multimodal_forecasts x, pt
                WHERE x.point_id = cp.point_id
                  AND x.data_date = pt.dd
                  AND x.daily_avg IS NOT NULL
            ) s
            ORDER BY is_past_or_today DESC,
                     CASE WHEN is_past_or_today THEN forecast_date END DESC,
                     forecast_date ASC
            LIMIT 1
        ) f ON TRUE
        WHERE cp.geom && tile_bbox
          AND (NOT use_whca OR cp.whca_selected = true)
          AND (pc_arr IS NULL OR cp.country_code = ANY(pc_arr))
          AND (cp.station_type = 'gauging'
               OR EXISTS (
                   SELECT 1 FROM gha.multimodal_forecasts mf0
                   WHERE mf0.point_id = cp.point_id
                     AND mf0.data_date >= CURRENT_DATE - INTERVAL '14 days'
               ))
    ) AS tile
    WHERE tile.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$

;
