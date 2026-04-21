-- ============================================================================
-- Make gha.multimodal_points_alerts use each POINT's own latest data_date
-- when no explicit `date` is passed — instead of the global MAX(data_date).
--
-- Why: different syncs (GeoSFM vs Mike vs FloodProofs) run on different
-- schedules, so some points lag a day behind others. Using the global
-- MAX meant those lagging points showed as grey/normal on the map even
-- though their chart was surfacing threshold-crossing values from a
-- day-old forecast. Users saw contradictory map vs chart.
-- ============================================================================

CREATE OR REPLACE FUNCTION gha.multimodal_points_alerts(
    z integer, x integer, y integer,
    date text DEFAULT ''::text,
    project_countries text DEFAULT ''::text,
    scope text DEFAULT ''::text
)
RETURNS bytea
LANGUAGE plpgsql STABLE PARALLEL SAFE
AS $$
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

    -- When the caller passes an explicit date, honour it. Otherwise each
    -- point falls back to its own latest in the subquery below.
    IF date IS NOT NULL AND date <> '' THEN
        query_date := date::date;
    END IF;

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
        LEFT JOIN LATERAL (
            SELECT daily_avg
            FROM gha.multimodal_forecasts f
            WHERE f.point_id = cp.point_id
              AND (query_date IS NULL OR f.data_date = query_date)
              AND f.daily_avg IS NOT NULL
            -- Most-recent data_date, then nearest-term forecast within it
            ORDER BY f.data_date DESC, f.forecast_date ASC
            LIMIT 1
        ) f ON TRUE
        WHERE cp.geom && tile_bbox
          AND (NOT use_whca OR cp.whca_selected = true)
          AND (pc_arr IS NULL OR cp.country_code = ANY(pc_arr))
    ) AS tile
    WHERE tile.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, ''::bytea);
END;
$$;
