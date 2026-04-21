-- ============================================================================
-- Redefine gha.multimodal_points_alerts to route classification through
-- gha.classify_alert() — same percentile-aware logic used by the clustered
-- forecast tiles. Replaces the old dual-branch function that hand-rolled
-- its own per-point thresholds using the legacy (warning/alarm/emergency)
-- column names.
--
-- Signature preserved so tile URLs and the "Multi Model" dataset keep
-- working without frontend changes.
-- ============================================================================

CREATE OR REPLACE FUNCTION gha.multimodal_points_alerts(
    z integer,
    x integer,
    y integer,
    date text DEFAULT ''::text,
    project_countries text DEFAULT ''::text,
    scope text DEFAULT ''::text
)
RETURNS bytea
LANGUAGE plpgsql STABLE PARALLEL SAFE
AS $function$
DECLARE
    tile_env  geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    query_date date;
    query_forecast_date date;
    mvt bytea;
    pc_arr text[];
    use_whca boolean := (scope IS NOT NULL AND lower(trim(scope)) = 'whca');
BEGIN
    IF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        pc_arr := string_to_array(project_countries, ',');
    END IF;

    IF date IS NOT NULL AND date <> '' THEN
        query_date := date::date;
    ELSE
        SELECT MAX(data_date) INTO query_date FROM gha.multimodal_forecasts;
    END IF;
    IF query_date IS NULL THEN
        RETURN ''::bytea;
    END IF;

    SELECT MIN(forecast_date) INTO query_forecast_date
    FROM gha.multimodal_forecasts
    WHERE data_date = query_date AND forecast_date >= query_date;

    SELECT ST_AsMVT(tile, 'gha.multimodal_points_alerts', 4096, 'mvt_geom')
    INTO mvt
    FROM (
        SELECT
            cp.point_id,
            cp.country_code,
            cp.whca_selected,
            cp.station_type,
            cp.zone,
            cp.admin_name,
            COALESCE(f.daily_avg, 0) AS daily_avg,
            gha.classify_alert(cp.point_id, f.daily_avg) AS alert_level,
            gha.alert_priority(gha.classify_alert(cp.point_id, f.daily_avg)) AS alert_priority,
            ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
        FROM gha.multimodal_control_points cp
        LEFT JOIN gha.multimodal_forecasts f
          ON f.point_id = cp.point_id
         AND f.data_date = query_date
         AND f.forecast_date = query_forecast_date
        WHERE cp.geom && tile_bbox
          AND (NOT use_whca OR cp.whca_selected = true)
          AND (pc_arr IS NULL OR cp.country_code = ANY(pc_arr))
    ) AS tile
    WHERE tile.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;
