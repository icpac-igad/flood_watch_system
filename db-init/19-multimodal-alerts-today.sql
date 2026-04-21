-- ============================================================================
-- Tile alert classification uses TODAY's forecast discharge per point
-- (forecast_date matching CURRENT_DATE when available; otherwise the
-- nearest forecast date). Compared against THAT point's own percentile
-- thresholds.
--
-- Supersedes 17-multimodal-points-per-point-date.sql — same idea but
-- "today's value" instead of "nearest-term of latest data_date" so the
-- dot reflects what's happening *today at this river*, not the run-out
-- horizon peak or a day-old near-term forecast.
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
            COALESCE(f.daily_avg, 0) AS daily_avg,
            gha.classify_alert(cp.point_id, f.daily_avg) AS alert_level,
            gha.alert_priority(gha.classify_alert(cp.point_id, f.daily_avg)) AS alert_priority,
            ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
        FROM gha.multimodal_control_points cp
        LEFT JOIN LATERAL (
            -- Most-recent data_date we have for this point (or the caller's
            -- override) …
            WITH pt AS (
                SELECT MAX(data_date) AS dd
                FROM gha.multimodal_forecasts
                WHERE point_id = cp.point_id
                  AND (query_date IS NULL OR data_date = query_date)
            )
            -- … pick the latest forecast_date *not in the future* (i.e. today
            -- or yesterday if today's value wasn't issued yet). If this run
            -- only has future dates (happens for brand-new points), fall back
            -- to the earliest future forecast inside the run.
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
            ORDER BY
                -- past-or-today first, then "earliest future" as fallback
                is_past_or_today DESC,
                CASE WHEN is_past_or_today THEN forecast_date END DESC,
                forecast_date ASC
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
