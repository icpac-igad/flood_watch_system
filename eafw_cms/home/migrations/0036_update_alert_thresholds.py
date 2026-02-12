from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0035_increase_cluster_grid_size"),
    ]

    operations = [
        # Update alert thresholds from 450/300/150 to 750/500/300
        # emergency >= 750, alarm >= 500, warning >= 300, normal < 300
        migrations.RunSQL(
            sql=r"""
-- =============================================================================
-- Main clustered function — updated thresholds
-- =============================================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_clustered(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL::text
) RETURNS bytea LANGUAGE plpgsql STABLE PARALLEL SAFE AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 40.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    mvt bytea;
BEGIN
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
    WHERE data_date = query_date AND forecast_date >= query_date;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered', 4096, 'mvt_geom') INTO mvt
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
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            WHERE cp.geom && tile_bbox_4326
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered', 4096, 'mvt_geom') INTO mvt
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
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                WHERE cp.geom && tile_bbox_4326
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;


-- =============================================================================
-- WHCA clustered function — updated thresholds
-- =============================================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_clustered_whca(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL::text,
    country_name text DEFAULT NULL::text,
    region_name text DEFAULT NULL::text,
    district_name text DEFAULT NULL::text
) RETURNS bytea LANGUAGE plpgsql STABLE PARALLEL SAFE AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 40.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    admin_geom geometry := NULL;
    mvt bytea;
BEGIN
    IF date IS NOT NULL AND date != '' THEN
        query_date := date::date;
    ELSE
        SELECT MAX(data_date) INTO query_date FROM gha.multimodal_forecasts;
    END IF;

    SELECT MIN(forecast_date) INTO query_forecast_date
    FROM gha.multimodal_forecasts
    WHERE data_date = query_date AND forecast_date >= query_date;

    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin2
        WHERE LOWER(name_2) = LOWER(district_name)
          AND (country_name IS NULL OR LOWER(country) = LOWER(country_name))
          AND (region_name IS NULL OR LOWER(name_1) = LOWER(region_name))
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin1
        WHERE LOWER(name_1) = LOWER(region_name)
          AND (country_name IS NULL OR LOWER(country) = LOWER(country_name))
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin0
        WHERE LOWER(country) = LOWER(country_name)
        LIMIT 1;
    END IF;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered_whca', 4096, 'mvt_geom') INTO mvt
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
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            WHERE cp.geom && tile_bbox_4326
              AND cp.whca_selected = true
              AND (admin_geom IS NULL OR ST_Within(cp.geom, admin_geom))
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered_whca', 4096, 'mvt_geom') INTO mvt
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
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                WHERE cp.geom && tile_bbox_4326
                  AND cp.whca_selected = true
                  AND (admin_geom IS NULL OR ST_Within(cp.geom, admin_geom))
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;


-- =============================================================================
-- Project-filtered function — updated thresholds
-- =============================================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_by_project(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL::text,
    project_countries text DEFAULT NULL::text,
    country_name text DEFAULT NULL::text,
    region_name text DEFAULT NULL::text,
    district_name text DEFAULT NULL::text
) RETURNS bytea LANGUAGE plpgsql STABLE PARALLEL SAFE AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 40.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    filter_geom geometry := NULL;
    countries_arr text[];
    mvt bytea;
BEGIN
    IF project_countries IS NOT NULL AND project_countries != '' THEN
        countries_arr := string_to_array(project_countries, ',');
        SELECT ST_Union(geom) INTO filter_geom FROM gha.admin0 WHERE country = ANY(countries_arr);
    END IF;

    IF date IS NOT NULL AND date != '' THEN
        query_date := date::date;
    ELSE
        SELECT MAX(data_date) INTO query_date FROM gha.multimodal_forecasts;
    END IF;

    SELECT MIN(forecast_date) INTO query_forecast_date
    FROM gha.multimodal_forecasts
    WHERE data_date = query_date AND forecast_date >= query_date;

    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin2
        WHERE LOWER(name_2) = LOWER(district_name)
          AND (country_name IS NULL OR LOWER(country) = LOWER(country_name))
          AND (region_name IS NULL OR LOWER(name_1) = LOWER(region_name))
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin1
        WHERE LOWER(name_1) = LOWER(region_name)
          AND (country_name IS NULL OR LOWER(country) = LOWER(country_name))
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin0
        WHERE LOWER(country) = LOWER(country_name)
        LIMIT 1;
    END IF;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_project', 4096, 'mvt_geom') INTO mvt
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
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            WHERE cp.geom && tile_bbox_4326
              AND (filter_geom IS NULL OR ST_Within(cp.geom, filter_geom))
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_project', 4096, 'mvt_geom') INTO mvt
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
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                WHERE cp.geom && tile_bbox_4326
                  AND (filter_geom IS NULL OR ST_Within(cp.geom, filter_geom))
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;


-- =============================================================================
-- Basin-filtered function — updated thresholds
-- =============================================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_by_basin(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL::text,
    basin_id bigint DEFAULT NULL::bigint
) RETURNS bytea LANGUAGE plpgsql STABLE PARALLEL SAFE AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 40.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    mvt bytea;
BEGIN
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
    WHERE data_date = query_date AND forecast_date >= query_date;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_basin', 4096, 'mvt_geom') INTO mvt
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
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            WHERE cp.geom && tile_bbox_4326
              AND (basin_id IS NULL OR cp.hybas_id = basin_id)
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_basin', 4096, 'mvt_geom') INTO mvt
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
                SELECT cp.point_id, f.data_date, f.daily_avg, f.daily_max, cp.x as px, cp.y as py, cp.geom
                FROM gha.multimodal_control_points cp
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                WHERE cp.geom && tile_bbox_4326
                  AND (basin_id IS NULL OR cp.hybas_id = basin_id)
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;


-- =============================================================================
-- Admin-filtered function — updated thresholds
-- =============================================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_by_admin(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 10,
    country_name text DEFAULT NULL::text,
    region_name text DEFAULT NULL::text,
    district_name text DEFAULT NULL::text
) RETURNS bytea LANGUAGE plpgsql STABLE PARALLEL SAFE AS $function$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
    grid_size float;
    filter_geom geometry;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);
    grid_size := 20.0 / power(2, z);

    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin2
        WHERE name_2 = district_name
          AND (region_name IS NULL OR region_name = '' OR name_1 = region_name)
          AND (country_name IS NULL OR country_name = '' OR country = country_name)
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin1
        WHERE name_1 = region_name
          AND (country_name IS NULL OR country_name = '' OR country = country_name)
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin0
        WHERE country = country_name
        LIMIT 1;
    END IF;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                m.id, m.point_id, m.zone, m.gridcode, m.has_data, m.admin_name,
                m.data_date::text AS data_date, m.forecast_date::text AS forecast_date,
                m.daily_avg, m.daily_max, m.daily_min,
                m.geosfm, m.floodproof, m.mike_hydro_rfe, m.mike_hydro_chirp, m.mike_hydro_imerg,
                m.forecasts_json::text AS forecasts_json,
                CASE WHEN m.daily_avg >= 750 THEN 'emergency' WHEN m.daily_avg >= 500 THEN 'alarm' WHEN m.daily_avg >= 300 THEN 'warning' ELSE 'normal' END AS alert_level,
                CASE WHEN m.daily_avg >= 750 THEN 4 WHEN m.daily_avg >= 500 THEN 3 WHEN m.daily_avg >= 300 THEN 2 ELSE 1 END AS alert_priority,
                1 AS point_count,
                ST_AsMVTGeom(ST_Transform(m.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_points m
            WHERE m.geom && tile_bbox_4326
              AND (filter_geom IS NULL OR ST_Within(m.geom, filter_geom))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(m.id) AS id, count(*) AS point_count, max(m.daily_max) AS daily_max,
                avg(m.daily_avg)::numeric(10,2) AS daily_avg, min(m.data_date)::text AS data_date,
                CASE WHEN max(m.daily_avg) >= 750 THEN 'emergency' WHEN max(m.daily_avg) >= 500 THEN 'alarm' WHEN max(m.daily_avg) >= 300 THEN 'warning' ELSE 'normal' END AS alert_level,
                CASE WHEN max(m.daily_avg) >= 750 THEN 4 WHEN max(m.daily_avg) >= 500 THEN 3 WHEN max(m.daily_avg) >= 300 THEN 2 ELSE 1 END AS alert_priority,
                sum(CASE WHEN m.daily_avg >= 750 THEN 1 ELSE 0 END)::integer AS emergency_count,
                sum(CASE WHEN m.daily_avg >= 500 AND m.daily_avg < 750 THEN 1 ELSE 0 END)::integer AS alarm_count,
                sum(CASE WHEN m.daily_avg >= 300 AND m.daily_avg < 500 THEN 1 ELSE 0 END)::integer AS warning_count,
                sum(CASE WHEN m.daily_avg < 300 OR m.daily_avg IS NULL THEN 1 ELSE 0 END)::integer AS normal_count,
                false AS has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(m.geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_points m
            WHERE m.geom && tile_bbox_4326
              AND (filter_geom IS NULL OR ST_Within(m.geom, filter_geom))
            GROUP BY floor(ST_X(m.geom) / grid_size), floor(ST_Y(m.geom) / grid_size)
            HAVING count(*) >= 1
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;
""",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
