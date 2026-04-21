-- ============================================================================
-- Tile alert classification uses PEAK daily_avg across the forecast horizon
-- (not just the nearest-term value).
--
-- Why: ingestion produces ~16 days of forecast per point. Previously the
-- map coloured each dot by day-0 flow; a point whose forecast spikes on
-- day 10 would stay grey on the map while the chart clearly showed the
-- upcoming exceedance. Users (correctly) flagged this as contradictory.
-- Now any day in the horizon crossing the point's own p90/p95/p99 lights
-- the dot — you can see the alert coming, not just "has it hit yet".
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
            COALESCE(f.current_avg, 0)  AS daily_avg,
            COALESCE(f.peak_avg,    0)  AS peak_avg,
            f.peak_date,
            -- Alert level = worst classification over the whole forecast
            -- horizon. So a point that spikes in 5 days lights up today.
            gha.classify_alert(cp.point_id, f.peak_avg) AS alert_level,
            gha.alert_priority(gha.classify_alert(cp.point_id, f.peak_avg)) AS alert_priority,
            ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
        FROM gha.multimodal_control_points cp
        LEFT JOIN LATERAL (
            WITH pt_latest AS (
                SELECT MAX(data_date) AS dd
                FROM gha.multimodal_forecasts
                WHERE point_id = cp.point_id
                  AND (query_date IS NULL OR data_date = query_date)
            )
            SELECT
                -- current = nearest-term forecast within that data_date
                (SELECT daily_avg FROM gha.multimodal_forecasts x
                  WHERE x.point_id = cp.point_id AND x.data_date = pt_latest.dd
                    AND x.daily_avg IS NOT NULL
                  ORDER BY x.forecast_date ASC LIMIT 1) AS current_avg,
                -- peak = max across the whole horizon of that data_date
                (SELECT MAX(daily_avg) FROM gha.multimodal_forecasts x
                  WHERE x.point_id = cp.point_id AND x.data_date = pt_latest.dd
                    AND x.daily_avg IS NOT NULL) AS peak_avg,
                -- the date the peak occurs (for popup/tooltip display)
                (SELECT forecast_date FROM gha.multimodal_forecasts x
                  WHERE x.point_id = cp.point_id AND x.data_date = pt_latest.dd
                    AND x.daily_avg IS NOT NULL
                  ORDER BY x.daily_avg DESC, x.forecast_date ASC LIMIT 1) AS peak_date
            FROM pt_latest
            WHERE pt_latest.dd IS NOT NULL
        ) f ON TRUE
        WHERE cp.geom && tile_bbox
          AND (NOT use_whca OR cp.whca_selected = true)
          AND (pc_arr IS NULL OR cp.country_code = ANY(pc_arr))
    ) AS tile
    WHERE tile.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, ''::bytea);
END;
$$;
