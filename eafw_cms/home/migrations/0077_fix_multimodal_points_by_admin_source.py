from django.db import migrations


FORWARD_SQL = """
DROP FUNCTION IF EXISTS gha.multimodal_points_by_admin(
    integer, integer, integer, integer, text, text, text
);

CREATE OR REPLACE FUNCTION gha.multimodal_points_by_admin(
    z integer,
    x integer,
    y integer,
    cluster_zoom integer DEFAULT 10,
    country_name text DEFAULT NULL::text,
    region_name text DEFAULT NULL::text,
    district_name text DEFAULT NULL::text
) RETURNS bytea
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 20.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    filter_geom geometry := NULL;
    mvt bytea;
BEGIN
    SELECT MAX(data_date) INTO query_date
    FROM gha.multimodal_forecasts;

    IF query_date IS NULL THEN
        RETURN ''::bytea;
    END IF;

    SELECT MIN(forecast_date) INTO query_forecast_date
    FROM gha.multimodal_forecasts
    WHERE data_date = query_date
      AND forecast_date >= query_date;

    IF query_forecast_date IS NULL THEN
        SELECT MIN(forecast_date) INTO query_forecast_date
        FROM gha.multimodal_forecasts
        WHERE data_date = query_date;
    END IF;

    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO filter_geom
        FROM gha.admin2
        WHERE LOWER(name_2) = LOWER(district_name)
          AND (region_name IS NULL OR region_name = '' OR LOWER(name_1) = LOWER(region_name))
          AND (country_name IS NULL OR country_name = '' OR LOWER(country) = LOWER(country_name))
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO filter_geom
        FROM gha.admin1
        WHERE LOWER(name_1) = LOWER(region_name)
          AND (country_name IS NULL OR country_name = '' OR LOWER(country) = LOWER(country_name))
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO filter_geom
        FROM gha.admin0
        WHERE LOWER(country) = LOWER(country_name)
        LIMIT 1;
    END IF;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                cp.point_id AS id,
                cp.point_id,
                cp.zone,
                cp.gridcode,
                (f.point_id IS NOT NULL) AS has_data,
                cp.admin_name,
                f.data_date::text AS data_date,
                f.forecast_date::text AS forecast_date,
                f.daily_avg,
                f.daily_max,
                f.daily_min,
                f.geosfm,
                f.floodproof,
                f.mike_hydro_rfe,
                f.mike_hydro_chirp,
                f.mike_hydro_imerg,
                COALESCE((
                    SELECT json_agg(json_build_object(
                        'date', fc.forecast_date,
                        'daily_avg', fc.daily_avg,
                        'daily_max', fc.daily_max,
                        'daily_min', fc.daily_min,
                        'GeoSFM', fc.geosfm,
                        'Floodproof', fc.floodproof,
                        'Mike_Hydro_RFE', fc.mike_hydro_rfe,
                        'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
                        'Mike_Hydro_IMERG', fc.mike_hydro_imerg
                    ) ORDER BY fc.forecast_date)
                    FROM gha.multimodal_forecasts fc
                    WHERE fc.point_id = cp.point_id
                      AND fc.data_date = query_date
                ), '[]'::json)::text AS forecasts_json,
                CASE
                    WHEN f.daily_avg >= 750 THEN 'emergency'
                    WHEN f.daily_avg >= 500 THEN 'alarm'
                    WHEN f.daily_avg >= 300 THEN 'warning'
                    ELSE 'normal'
                END AS alert_level,
                CASE
                    WHEN f.daily_avg >= 750 THEN 4
                    WHEN f.daily_avg >= 500 THEN 3
                    WHEN f.daily_avg >= 300 THEN 2
                    ELSE 1
                END AS alert_priority,
                1 AS point_count,
                ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_control_points cp
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date
                AND f.forecast_date = query_forecast_date
            WHERE cp.geom && tile_bbox_4326
              AND (filter_geom IS NULL OR ST_Within(cp.geom, filter_geom))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(point_id) AS id,
                count(*) AS point_count,
                max(daily_max) AS daily_max,
                avg(daily_avg)::numeric(10,2) AS daily_avg,
                min(data_date)::text AS data_date,
                CASE
                    WHEN max(daily_avg) >= 750 THEN 'emergency'
                    WHEN max(daily_avg) >= 500 THEN 'alarm'
                    WHEN max(daily_avg) >= 300 THEN 'warning'
                    ELSE 'normal'
                END AS alert_level,
                CASE
                    WHEN max(daily_avg) >= 750 THEN 4
                    WHEN max(daily_avg) >= 500 THEN 3
                    WHEN max(daily_avg) >= 300 THEN 2
                    ELSE 1
                END AS alert_priority,
                sum(CASE WHEN daily_avg >= 750 THEN 1 ELSE 0 END)::integer AS emergency_count,
                sum(CASE WHEN daily_avg >= 500 AND daily_avg < 750 THEN 1 ELSE 0 END)::integer AS alarm_count,
                sum(CASE WHEN daily_avg >= 300 AND daily_avg < 500 THEN 1 ELSE 0 END)::integer AS warning_count,
                sum(CASE WHEN daily_avg < 300 OR daily_avg IS NULL THEN 1 ELSE 0 END)::integer AS normal_count,
                false AS has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM (
                SELECT
                    cp.point_id,
                    f.data_date,
                    f.daily_avg,
                    f.daily_max,
                    cp.x AS px,
                    cp.y AS py,
                    cp.geom
                FROM gha.multimodal_control_points cp
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date
                    AND f.forecast_date = query_forecast_date
                WHERE cp.geom && tile_bbox_4326
                  AND (filter_geom IS NULL OR ST_Within(cp.geom, filter_geom))
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0076_add_clipping_to_wrf_rainfall_tiles"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
