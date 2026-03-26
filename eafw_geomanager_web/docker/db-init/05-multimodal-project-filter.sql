-- Add optional project_countries clipping to multimodal vector tiles.
--
-- The homepage minimap appends project_countries based on the configured
-- site countries. Use a dedicated pg_tileserv function name here so it does
-- not collide with the legacy gha.multimodal_points_clustered(date, zoom)
-- overload that pg_tileserv already exposes.

CREATE OR REPLACE FUNCTION gha.multimodal_points_clustered_project(
    z integer,
    x integer,
    y integer,
    cluster_zoom integer DEFAULT 7,
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
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 40.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    countries_arr text[] := NULL;
    mvt bytea;
BEGIN
    IF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        countries_arr := regexp_split_to_array(upper(project_countries), '\s*,\s*');
    END IF;

    IF date IS NOT NULL AND date != '' THEN
        BEGIN
            query_date := date::date;
        EXCEPTION WHEN OTHERS THEN
            SELECT MAX(data_date) INTO query_date FROM gha.multimodal_forecasts;
        END;
    ELSE
        SELECT MAX(data_date) INTO query_date FROM gha.multimodal_forecasts;
    END IF;

    SELECT MIN(forecast_date) INTO query_forecast_date
    FROM gha.multimodal_forecasts
    WHERE data_date = query_date
      AND forecast_date >= query_date;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered_project', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                cp.point_id as id, cp.point_id, cp.zone, cp.gridcode,
                (f.point_id IS NOT NULL) as has_data,
                cp.admin_name, f.data_date::text as data_date, cp.hybas_id,
                f.forecast_date::text as forecast_date,
                f.daily_avg, f.daily_max, f.daily_min,
                f.geosfm, f.floodproof, f.mike_hydro_rfe, f.mike_hydro_chirp, f.mike_hydro_imerg,
                COALESCE((
                    SELECT json_agg(json_build_object(
                        'date', fc.forecast_date, 'daily_avg', fc.daily_avg,
                        'daily_max', fc.daily_max, 'daily_min', fc.daily_min,
                        'GeoSFM', fc.geosfm, 'Floodproof', fc.floodproof,
                        'Mike_Hydro_RFE', fc.mike_hydro_rfe,
                        'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
                        'Mike_Hydro_IMERG', fc.mike_hydro_imerg
                    ) ORDER BY fc.forecast_date)
                    FROM gha.multimodal_forecasts fc
                    WHERE fc.point_id = cp.point_id AND fc.data_date = query_date
                ), '[]'::json)::text as forecasts_json,
                CASE WHEN f.daily_avg >= 750 THEN 'emergency'
                     WHEN f.daily_avg >= 500 THEN 'alarm'
                     WHEN f.daily_avg >= 300 THEN 'warning'
                     ELSE 'normal' END as alert_level,
                CASE WHEN f.daily_avg >= 750 THEN 4
                     WHEN f.daily_avg >= 500 THEN 3
                     WHEN f.daily_avg >= 300 THEN 2
                     ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_control_points cp
            LEFT JOIN LATERAL (
                SELECT COALESCE(
                    NULLIF(
                        CASE UPPER(TRIM(COALESCE(cp.country_code, '')))
                            WHEN 'BI' THEN 'BURUNDI'
                            WHEN 'DJ' THEN 'DJIBOUTI'
                            WHEN 'ER' THEN 'ERITREA'
                            WHEN 'ET' THEN 'ETHIOPIA'
                            WHEN 'KE' THEN 'KENYA'
                            WHEN 'RW' THEN 'RWANDA'
                            WHEN 'SD' THEN 'SUDAN'
                            WHEN 'SO' THEN 'SOMALIA'
                            WHEN 'SS' THEN 'SOUTH SUDAN'
                            WHEN 'TZ' THEN 'TANZANIA'
                            WHEN 'UG' THEN 'UGANDA'
                            ELSE ''
                        END,
                        ''
                    ),
                    (
                        SELECT UPPER(TRIM(a0.country))
                        FROM gha.admin0 a0
                        WHERE a0.geom && cp.geom
                          AND ST_Within(cp.geom, a0.geom)
                        LIMIT 1
                    )
                ) AS country_name
            ) cc ON TRUE
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            WHERE cp.geom && tile_bbox_4326
              AND (countries_arr IS NULL OR cc.country_name = ANY(countries_arr))
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered_project', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(point_id) as id, count(*) as point_count,
                max(daily_max) as daily_max, avg(daily_avg)::numeric(10,2) as daily_avg,
                min(data_date)::text as data_date,
                CASE WHEN max(daily_avg) >= 750 THEN 'emergency'
                     WHEN max(daily_avg) >= 500 THEN 'alarm'
                     WHEN max(daily_avg) >= 300 THEN 'warning'
                     ELSE 'normal' END as alert_level,
                CASE WHEN max(daily_avg) >= 750 THEN 4
                     WHEN max(daily_avg) >= 500 THEN 3
                     WHEN max(daily_avg) >= 300 THEN 2
                     ELSE 1 END as alert_priority,
                sum(CASE WHEN daily_avg >= 750 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN daily_avg >= 500 AND daily_avg < 750 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN daily_avg >= 300 AND daily_avg < 500 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN daily_avg < 300 OR daily_avg IS NULL THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM (
                SELECT cp.point_id, f.data_date, f.daily_avg, f.daily_max,
                       cp.x as px, cp.y as py, cp.geom
                FROM gha.multimodal_control_points cp
                LEFT JOIN LATERAL (
                    SELECT COALESCE(
                        NULLIF(
                            CASE UPPER(TRIM(COALESCE(cp.country_code, '')))
                                WHEN 'BI' THEN 'BURUNDI'
                                WHEN 'DJ' THEN 'DJIBOUTI'
                                WHEN 'ER' THEN 'ERITREA'
                                WHEN 'ET' THEN 'ETHIOPIA'
                                WHEN 'KE' THEN 'KENYA'
                                WHEN 'RW' THEN 'RWANDA'
                                WHEN 'SD' THEN 'SUDAN'
                                WHEN 'SO' THEN 'SOMALIA'
                                WHEN 'SS' THEN 'SOUTH SUDAN'
                                WHEN 'TZ' THEN 'TANZANIA'
                                WHEN 'UG' THEN 'UGANDA'
                                ELSE ''
                            END,
                            ''
                        ),
                        (
                            SELECT UPPER(TRIM(a0.country))
                            FROM gha.admin0 a0
                            WHERE a0.geom && cp.geom
                              AND ST_Within(cp.geom, a0.geom)
                            LIMIT 1
                        )
                    ) AS country_name
                ) cc ON TRUE
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                WHERE cp.geom && tile_bbox_4326
                  AND (countries_arr IS NULL OR cc.country_name = ANY(countries_arr))
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.multimodal_points_clustered_project(integer, integer, integer, integer, text, text) TO PUBLIC;
