# Migration: Use per-point thresholds from gha.point_alert_thresholds
# in all pg_tileserv vector tile functions, so cluster alert levels
# match the individual point alert levels shown after zoom-in.
#
# Also: replace admin_name LIKE prefix matching with ST_Within for
# WHCA filtering — ensures points outside country boundaries are excluded.
#
# Previously: hardcoded 300/500/750 thresholds, admin_name LIKE 'UG%' etc.
# Now: COALESCE(pt.*_threshold, fallback) per point, ST_Within(geom, whca_union)

from django.db import migrations


FORWARD_SQL = r"""
-- ============================================================
-- 1. gha.multimodal_points_clustered  (all points, no WHCA filter)
--    Per-point thresholds only.
-- ============================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_clustered(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql STABLE
AS $fn$
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
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 'emergency'
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 'alarm'
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 'warning'
                     ELSE 'normal' END as alert_level,
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                     ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_control_points cp
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            LEFT JOIN gha.point_alert_thresholds pt
                ON pt.point_id = cp.point_id
            WHERE cp.geom && tile_bbox_4326
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(point_id) as id, count(*) as point_count,
                max(daily_max) as daily_max, avg(daily_avg)::numeric(10,2) as daily_avg,
                min(data_date)::text as data_date,
                CASE WHEN max(pt_alert) >= 4 THEN 'emergency'
                     WHEN max(pt_alert) >= 3 THEN 'alarm'
                     WHEN max(pt_alert) >= 2 THEN 'warning'
                     ELSE 'normal' END as alert_level,
                max(pt_alert) as alert_priority,
                sum(CASE WHEN pt_alert >= 4 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN pt_alert = 3 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN pt_alert = 2 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN pt_alert <= 1 THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM (
                SELECT cp.point_id, f.data_date, f.daily_avg, f.daily_max,
                       cp.x as px, cp.y as py, cp.geom,
                       CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                            WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                            WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                            ELSE 1 END as pt_alert
                FROM gha.multimodal_control_points cp
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                LEFT JOIN gha.point_alert_thresholds pt
                    ON pt.point_id = cp.point_id
                WHERE cp.geom && tile_bbox_4326
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$fn$;


-- ============================================================
-- 2. gha.multimodal_points_clustered_whca
--    Per-point thresholds + ST_Within for WHCA boundary filtering
-- ============================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_clustered_whca(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql STABLE
AS $fn$
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

    -- Resolve admin geometry filter (further narrows within WHCA)
    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin2
        WHERE LOWER(name_2) = LOWER(district_name) LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin1
        WHERE LOWER(name_1) = LOWER(region_name) LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin0
        WHERE LOWER(country) = LOWER(country_name) LIMIT 1;
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
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 'emergency'
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 'alarm'
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 'warning'
                     ELSE 'normal' END as alert_level,
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                     ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_control_points cp
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            LEFT JOIN gha.point_alert_thresholds pt
                ON pt.point_id = cp.point_id
            WHERE cp.geom && tile_bbox_4326
              AND cp.whca_selected IS TRUE
              AND (admin_geom IS NULL OR ST_Within(cp.geom, admin_geom))
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_clustered_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(point_id) as id, count(*) as point_count,
                max(daily_max) as daily_max, avg(daily_avg)::numeric(10,2) as daily_avg,
                min(data_date)::text as data_date,
                CASE WHEN max(pt_alert) >= 4 THEN 'emergency'
                     WHEN max(pt_alert) >= 3 THEN 'alarm'
                     WHEN max(pt_alert) >= 2 THEN 'warning'
                     ELSE 'normal' END as alert_level,
                max(pt_alert) as alert_priority,
                sum(CASE WHEN pt_alert >= 4 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN pt_alert = 3 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN pt_alert = 2 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN pt_alert <= 1 THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM (
                SELECT cp.point_id, f.data_date, f.daily_avg, f.daily_max,
                       cp.x as px, cp.y as py, cp.geom,
                       CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                            WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                            WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                            ELSE 1 END as pt_alert
                FROM gha.multimodal_control_points cp
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                LEFT JOIN gha.point_alert_thresholds pt
                    ON pt.point_id = cp.point_id
                WHERE cp.geom && tile_bbox_4326
                  AND ST_Within(cp.geom, whca_geom)
                  AND (admin_geom IS NULL OR ST_Within(cp.geom, admin_geom))
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$fn$;


-- ============================================================
-- 3. gha.multimodal_points_by_admin
--    Per-point thresholds (already uses ST_Within for admin filter)
-- ============================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_by_admin(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 10,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql STABLE
AS $fn$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 20.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    filter_geom geometry := NULL;
    mvt bytea;
BEGIN
    SELECT MAX(data_date) INTO query_date FROM gha.multimodal_forecasts;

    IF query_date IS NULL THEN
        RETURN ''::bytea;
    END IF;

    SELECT MIN(forecast_date) INTO query_forecast_date
    FROM gha.multimodal_forecasts
    WHERE data_date = query_date AND forecast_date >= query_date;

    IF query_forecast_date IS NULL THEN
        SELECT MIN(forecast_date) INTO query_forecast_date
        FROM gha.multimodal_forecasts WHERE data_date = query_date;
    END IF;

    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin2
        WHERE LOWER(name_2) = LOWER(district_name)
          AND (region_name IS NULL OR region_name = '' OR LOWER(name_1) = LOWER(region_name))
          AND (country_name IS NULL OR country_name = '' OR LOWER(country) = LOWER(country_name))
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin1
        WHERE LOWER(name_1) = LOWER(region_name)
          AND (country_name IS NULL OR country_name = '' OR LOWER(country) = LOWER(country_name))
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO filter_geom FROM gha.admin0
        WHERE LOWER(country) = LOWER(country_name) LIMIT 1;
    END IF;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                cp.point_id AS id, cp.point_id, cp.zone, cp.gridcode,
                (f.point_id IS NOT NULL) AS has_data,
                cp.admin_name,
                f.data_date::text AS data_date,
                f.forecast_date::text AS forecast_date,
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
                ), '[]'::json)::text AS forecasts_json,
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 'emergency'
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 'alarm'
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 'warning'
                     ELSE 'normal' END AS alert_level,
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                     ELSE 1 END AS alert_priority,
                1 AS point_count,
                ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_control_points cp
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            LEFT JOIN gha.point_alert_thresholds pt
                ON pt.point_id = cp.point_id
            WHERE cp.geom && tile_bbox_4326
              AND (filter_geom IS NULL OR ST_Within(cp.geom, filter_geom))
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(point_id) AS id, count(*) AS point_count,
                max(daily_max) AS daily_max, avg(daily_avg)::numeric(10,2) AS daily_avg,
                min(data_date)::text AS data_date,
                CASE WHEN max(pt_alert) >= 4 THEN 'emergency'
                     WHEN max(pt_alert) >= 3 THEN 'alarm'
                     WHEN max(pt_alert) >= 2 THEN 'warning'
                     ELSE 'normal' END AS alert_level,
                max(pt_alert) AS alert_priority,
                sum(CASE WHEN pt_alert >= 4 THEN 1 ELSE 0 END)::integer AS emergency_count,
                sum(CASE WHEN pt_alert = 3 THEN 1 ELSE 0 END)::integer AS alarm_count,
                sum(CASE WHEN pt_alert = 2 THEN 1 ELSE 0 END)::integer AS warning_count,
                sum(CASE WHEN pt_alert <= 1 THEN 1 ELSE 0 END)::integer AS normal_count,
                false AS has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM (
                SELECT cp.point_id, f.data_date, f.daily_avg, f.daily_max,
                       cp.x AS px, cp.y AS py, cp.geom,
                       CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                            WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                            WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                            ELSE 1 END as pt_alert
                FROM gha.multimodal_control_points cp
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                LEFT JOIN gha.point_alert_thresholds pt
                    ON pt.point_id = cp.point_id
                WHERE cp.geom && tile_bbox_4326
                  AND (filter_geom IS NULL OR ST_Within(cp.geom, filter_geom))
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$fn$;


-- ============================================================
-- 4. gha.multimodal_points_by_basin
--    Per-point thresholds
-- ============================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_by_basin(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL,
    basin_id bigint DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql STABLE
AS $fn$
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
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 'emergency'
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 'alarm'
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 'warning'
                     ELSE 'normal' END as alert_level,
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                     ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_control_points cp
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            LEFT JOIN gha.point_alert_thresholds pt
                ON pt.point_id = cp.point_id
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
                CASE WHEN max(pt_alert) >= 4 THEN 'emergency'
                     WHEN max(pt_alert) >= 3 THEN 'alarm'
                     WHEN max(pt_alert) >= 2 THEN 'warning'
                     ELSE 'normal' END as alert_level,
                max(pt_alert) as alert_priority,
                sum(CASE WHEN pt_alert >= 4 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN pt_alert = 3 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN pt_alert = 2 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN pt_alert <= 1 THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM (
                SELECT cp.point_id, f.data_date, f.daily_avg, f.daily_max,
                       cp.x as px, cp.y as py, cp.geom,
                       CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                            WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                            WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                            ELSE 1 END as pt_alert
                FROM gha.multimodal_control_points cp
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                LEFT JOIN gha.point_alert_thresholds pt
                    ON pt.point_id = cp.point_id
                WHERE cp.geom && tile_bbox_4326
                  AND (basin_id IS NULL OR cp.hybas_id = basin_id)
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$fn$;


-- ============================================================
-- 5. gha.multimodal_points_by_project
--    Per-point thresholds + ST_Within for country filtering
-- ============================================================
CREATE OR REPLACE FUNCTION gha.multimodal_points_by_project(
    z integer, x integer, y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL,
    project_countries text DEFAULT NULL,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql STABLE
AS $fn$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
    grid_size float := 40.0 / power(2, z);
    query_date date;
    query_forecast_date date;
    admin_geom geometry := NULL;
    project_geom geometry := NULL;
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

    -- Build union geometry for project countries using ST_Within
    IF project_countries IS NOT NULL AND project_countries != '' THEN
        SELECT ST_Union(a0.geom) INTO project_geom
        FROM gha.admin0 a0
        WHERE UPPER(a0.country) IN (
            SELECT UPPER(TRIM(unnest(string_to_array(project_countries, ','))))
        ) OR UPPER(a0.gid_0) IN (
            SELECT UPPER(TRIM(unnest(string_to_array(project_countries, ','))))
        );
    END IF;

    -- Resolve admin geometry filter
    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin2
        WHERE LOWER(name_2) = LOWER(district_name) LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin1
        WHERE LOWER(name_1) = LOWER(region_name) LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin0
        WHERE LOWER(country) = LOWER(country_name) LIMIT 1;
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
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 'emergency'
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 'alarm'
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 'warning'
                     ELSE 'normal' END as alert_level,
                CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                     WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                     WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                     ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(cp.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.multimodal_control_points cp
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = query_date AND f.forecast_date = query_forecast_date
            LEFT JOIN gha.point_alert_thresholds pt
                ON pt.point_id = cp.point_id
            WHERE cp.geom && tile_bbox_4326
              AND (project_geom IS NULL OR ST_Within(cp.geom, project_geom))
              AND (admin_geom IS NULL OR ST_Within(cp.geom, admin_geom))
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.multimodal_points_by_project', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(point_id) as id, count(*) as point_count,
                max(daily_max) as daily_max, avg(daily_avg)::numeric(10,2) as daily_avg,
                min(data_date)::text as data_date,
                CASE WHEN max(pt_alert) >= 4 THEN 'emergency'
                     WHEN max(pt_alert) >= 3 THEN 'alarm'
                     WHEN max(pt_alert) >= 2 THEN 'warning'
                     ELSE 'normal' END as alert_level,
                max(pt_alert) as alert_priority,
                sum(CASE WHEN pt_alert >= 4 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN pt_alert = 3 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN pt_alert = 2 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN pt_alert <= 1 THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM (
                SELECT cp.point_id, f.data_date, f.daily_avg, f.daily_max,
                       cp.x as px, cp.y as py, cp.geom,
                       CASE WHEN f.daily_avg >= COALESCE(pt.emergency_threshold, 750) THEN 4
                            WHEN f.daily_avg >= COALESCE(pt.alarm_threshold, 500) THEN 3
                            WHEN f.daily_avg >= COALESCE(pt.warning_threshold, 300) THEN 2
                            ELSE 1 END as pt_alert
                FROM gha.multimodal_control_points cp
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = query_date AND f.forecast_date = query_forecast_date
                LEFT JOIN gha.point_alert_thresholds pt
                    ON pt.point_id = cp.point_id
                WHERE cp.geom && tile_bbox_4326
                  AND (project_geom IS NULL OR ST_Within(cp.geom, project_geom))
                  AND (admin_geom IS NULL OR ST_Within(cp.geom, admin_geom))
            ) subq
            GROUP BY floor(px / grid_size), floor(py / grid_size)
            HAVING count(*) >= 1
        ) AS tile WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$fn$;


-- ============================================================
-- Grants & comments
-- ============================================================
GRANT EXECUTE ON FUNCTION gha.multimodal_points_clustered TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.multimodal_points_clustered_whca TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.multimodal_points_by_admin TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.multimodal_points_by_basin TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.multimodal_points_by_project TO PUBLIC;

COMMENT ON FUNCTION gha.multimodal_points_clustered IS 'Clustered multimodal forecast points using per-point thresholds from gha.point_alert_thresholds (fallback: 300/500/750).';
COMMENT ON FUNCTION gha.multimodal_points_clustered_whca IS 'WHCA filtered (ST_Within UG/RW/SS/ET/SD boundaries) clustered multimodal forecast points with per-point thresholds.';
COMMENT ON FUNCTION gha.multimodal_points_by_admin IS 'Admin-filtered multimodal forecast points with per-point thresholds.';
COMMENT ON FUNCTION gha.multimodal_points_by_basin IS 'Basin-filtered multimodal forecast points with per-point thresholds.';
COMMENT ON FUNCTION gha.multimodal_points_by_project IS 'Project-filtered (ST_Within country boundaries) multimodal forecast points with per-point thresholds.';
""";

REVERSE_SQL = r"""
-- Revert placeholder — the forward SQL is idempotent via CREATE OR REPLACE
SELECT 1;
""";


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0078_switch_raster_layers_to_titiler'),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
