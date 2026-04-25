-- Parameterised tile function: same data as `gha.multimodal_points_alerts`,
-- but classifies each point against ONE specific model column instead of
-- the daily-average. Lets the Wagtail sidebar expose Mike Hydro and
-- GeoSFM as separate map layers without copying data into a new table.
--
-- model_key accepts: daily_avg (default), geosfm, floodproof,
-- mike_hydro_rfe, mike_hydro_chirp, mike_hydro_imerg.

CREATE OR REPLACE FUNCTION gha.multimodal_points_by_model(
    z integer, x integer, y integer,
    model_key text DEFAULT 'daily_avg',
    date text DEFAULT '',
    scope text DEFAULT ''
)
RETURNS bytea
LANGUAGE plpgsql
STABLE PARALLEL SAFE
AS $function$
DECLARE
    tile_env  geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    query_date date;
    mvt bytea;
    use_whca boolean := (scope IS NOT NULL AND lower(trim(scope)) = 'whca');
    -- Guard against SQL injection via model_key — we never concatenate it,
    -- but we still narrow it to a known set.
    allowed boolean := (model_key = ANY (ARRAY[
        'daily_avg', 'geosfm', 'floodproof',
        'mike_hydro_rfe', 'mike_hydro_chirp', 'mike_hydro_imerg'
    ]));
BEGIN
    IF NOT allowed THEN
        model_key := 'daily_avg';
    END IF;

    IF date IS NOT NULL AND date <> '' THEN
        BEGIN
            query_date := date::date;
        EXCEPTION WHEN OTHERS THEN
            query_date := NULL;
        END;
    END IF;

    SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_model', 4096, 'mvt_geom')
    INTO mvt
    FROM (
        SELECT
            cp.point_id, cp.country_code, cp.whca_selected, cp.station_type,
            cp.zone, cp.admin_name,
            COALESCE(f.val, 0) AS discharge,
            model_key AS model,
            gha.classify_alert(cp.point_id, f.val) AS alert_level,
            gha.alert_priority(gha.classify_alert(cp.point_id, f.val)) AS alert_priority,
            ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
        FROM gha.multimodal_control_points cp
        LEFT JOIN LATERAL (
            WITH pt AS (
                SELECT MAX(data_date) AS dd
                FROM gha.multimodal_forecasts
                WHERE point_id = cp.point_id
                  AND (query_date IS NULL OR data_date = query_date)
            )
            SELECT
                CASE model_key
                    WHEN 'geosfm'           THEN x.geosfm
                    WHEN 'floodproof'       THEN x.floodproof
                    WHEN 'mike_hydro_rfe'   THEN x.mike_hydro_rfe
                    WHEN 'mike_hydro_chirp' THEN x.mike_hydro_chirp
                    WHEN 'mike_hydro_imerg' THEN x.mike_hydro_imerg
                    ELSE x.daily_avg
                END AS val
            FROM (
                SELECT *, (forecast_date <= CURRENT_DATE) AS is_past_or_today
                FROM gha.multimodal_forecasts, pt
                WHERE point_id = cp.point_id
                  AND data_date = pt.dd
                  AND CASE model_key
                      WHEN 'geosfm'           THEN geosfm
                      WHEN 'floodproof'       THEN floodproof
                      WHEN 'mike_hydro_rfe'   THEN mike_hydro_rfe
                      WHEN 'mike_hydro_chirp' THEN mike_hydro_chirp
                      WHEN 'mike_hydro_imerg' THEN mike_hydro_imerg
                      ELSE daily_avg
                  END IS NOT NULL
            ) x
            ORDER BY is_past_or_today DESC,
                     CASE WHEN is_past_or_today THEN forecast_date END DESC,
                     forecast_date ASC
            LIMIT 1
        ) f ON TRUE
        WHERE cp.geom && tile_bbox
          AND (NOT use_whca OR cp.whca_selected = true)
          -- Only render a point if it has data for the SELECTED model in
          -- recent runs. Without this, the GeoSFM/Mike layers showed every
          -- multimodal control point, painting the data-less ones grey and
          -- making the threshold view look noisier than reality. This
          -- filter is dynamic per `model_key` — no hardcoded model lists,
          -- no per-layer subqueries.
          AND EXISTS (
              SELECT 1 FROM gha.multimodal_forecasts mf0
              WHERE mf0.point_id = cp.point_id
                AND mf0.data_date >= CURRENT_DATE - INTERVAL '14 days'
                AND CASE model_key
                    WHEN 'geosfm'           THEN mf0.geosfm
                    WHEN 'floodproof'       THEN mf0.floodproof
                    WHEN 'mike_hydro_rfe'   THEN mf0.mike_hydro_rfe
                    WHEN 'mike_hydro_chirp' THEN mf0.mike_hydro_chirp
                    WHEN 'mike_hydro_imerg' THEN mf0.mike_hydro_imerg
                    ELSE mf0.daily_avg
                END IS NOT NULL
          )
    ) AS tile
    WHERE tile.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;
