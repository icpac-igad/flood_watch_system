-- Lightweight unclustered multimodal vector tiles.
--
-- The generic forecast provider function is useful for shared forecast
-- behavior, but multimodal needs a raw point mode that avoids embedding the
-- full forecast JSON in every tile. This keeps the point layer unclustered
-- without producing multi-megabyte low-zoom tiles.

CREATE OR REPLACE FUNCTION gha.multimodal_points_raw(
    z integer,
    x integer,
    y integer,
    date text DEFAULT NULL::text,
    project_countries text DEFAULT NULL::text
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(tile_bbox_3857, 4326);
    query_date date := NULL;
    countries_arr text[] := NULL;
    mvt bytea;
BEGIN
    IF project_countries IS NOT NULL
       AND trim(project_countries) <> ''
       AND trim(project_countries) <> '__none__' THEN
        countries_arr := regexp_split_to_array(upper(project_countries), '\s*,\s*');
    END IF;

    IF date IS NOT NULL AND trim(date) <> '' THEN
        BEGIN
            query_date := date::date;
        EXCEPTION WHEN OTHERS THEN
            query_date := NULL;
        END;
    END IF;

    IF query_date IS NULL THEN
        SELECT MAX(data_date) INTO query_date
        FROM gha.multimodal_forecasts;
    END IF;

    IF query_date IS NULL THEN
        RETURN ''::bytea;
    END IF;

    SELECT ST_AsMVT(tile, 'gha.multimodal_points_raw', 4096, 'mvt_geom') INTO mvt
    FROM (
        SELECT
            cp.point_id AS id,
            cp.point_id,
            cp.admin_name,
            cc.country_code,
            f.forecast_date::text AS forecast_date,
            f.daily_avg,
            f.daily_max,
            f.geosfm,
            f.floodproof,
            f.mike_hydro_rfe,
            f.mike_hydro_chirp,
            f.mike_hydro_imerg,
            CASE
                WHEN f.daily_avg >= 750 THEN 'emergency'
                WHEN f.daily_avg >= 500 THEN 'alarm'
                WHEN f.daily_avg >= 300 THEN 'warning'
                ELSE 'normal'
            END AS alert_level,
            ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
        FROM gha.multimodal_control_points cp
        LEFT JOIN LATERAL (
            SELECT
                COALESCE(
                    gha.normalize_country_name(cp.country_code),
                    (
                        SELECT UPPER(TRIM(a0.country))
                        FROM gha.admin0 a0
                        WHERE a0.geom && cp.geom
                          AND ST_Within(cp.geom, a0.geom)
                        LIMIT 1
                    )
                ) AS country_name,
                COALESCE(
                    gha.normalize_country_code(cp.country_code),
                    (
                        SELECT gha.normalize_country_code(a0.gid_0)
                        FROM gha.admin0 a0
                        WHERE a0.geom && cp.geom
                          AND ST_Within(cp.geom, a0.geom)
                        LIMIT 1
                    ),
                    'UN'
                ) AS country_code
        ) cc ON TRUE
        JOIN LATERAL (
            SELECT
                mf.forecast_date,
                mf.daily_avg,
                mf.daily_max,
                mf.geosfm,
                mf.floodproof,
                mf.mike_hydro_rfe,
                mf.mike_hydro_chirp,
                mf.mike_hydro_imerg
            FROM gha.multimodal_forecasts mf
            WHERE mf.point_id = cp.point_id
              AND mf.data_date = query_date
              AND mf.forecast_date >= query_date
            ORDER BY mf.forecast_date ASC
            LIMIT 1
        ) f ON TRUE
        WHERE cp.geom && tile_bbox_4326
          AND (
              countries_arr IS NULL
              OR cc.country_name = ANY(countries_arr)
              OR cc.country_code = ANY(countries_arr)
          )
    ) AS tile
    WHERE tile.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.multimodal_points_raw(integer, integer, integer, text, text) TO PUBLIC;
