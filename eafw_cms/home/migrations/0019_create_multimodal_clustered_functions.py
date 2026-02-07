# Generated migration to create multimodal_points_clustered functions for pg_tileserv
# Updated: Use daily_avg (average of all models) for alert level calculation
# Thresholds: Warning >= 150, Alarm >= 300, Emergency >= 450 m³/s

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0018_wave_animation_settings'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
-- Create multimodal_points_clustered function for pg_tileserv
-- Uses daily_avg (average of all models) for alert level calculation
-- Thresholds: Warning >= 150, Alarm >= 300, Emergency >= 450 m³/s
DROP FUNCTION IF EXISTS public.multimodal_points_clustered(integer, integer, integer, integer);

CREATE OR REPLACE FUNCTION public.multimodal_points_clustered(z integer, x integer, y integer, cluster_zoom integer DEFAULT 10)
 RETURNS bytea
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
    grid_size float;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);
    grid_size := 40.0 / power(2, z);

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'public.multimodal_points_clustered', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id, point_id, zone, gridcode, has_data, admin_name,
                data_date::text as data_date,
                forecast_date::text as forecast_date,
                daily_avg, daily_max, daily_min,
                geosfm, floodproof, mike_hydro_rfe, mike_hydro_chirp, mike_hydro_imerg,
                forecasts_json::text as forecasts_json,
                CASE WHEN daily_avg >= 450 THEN 'emergency' WHEN daily_avg >= 300 THEN 'alarm' WHEN daily_avg >= 150 THEN 'warning' ELSE 'normal' END as alert_level,
                CASE WHEN daily_avg >= 450 THEN 4 WHEN daily_avg >= 300 THEN 3 WHEN daily_avg >= 150 THEN 2 ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM public.multimodal_points
            WHERE geom && tile_bbox_4326
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'public.multimodal_points_clustered', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(id) as id, count(*) as point_count, max(daily_max) as daily_max,
                avg(daily_avg)::numeric(10,2) as daily_avg, min(data_date)::text as data_date,
                CASE WHEN max(daily_avg) >= 450 THEN 'emergency' WHEN max(daily_avg) >= 300 THEN 'alarm' WHEN max(daily_avg) >= 150 THEN 'warning' ELSE 'normal' END as alert_level,
                CASE WHEN max(daily_avg) >= 450 THEN 4 WHEN max(daily_avg) >= 300 THEN 3 WHEN max(daily_avg) >= 150 THEN 2 ELSE 1 END as alert_priority,
                sum(CASE WHEN daily_avg >= 450 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN daily_avg >= 300 AND daily_avg < 450 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN daily_avg >= 150 AND daily_avg < 300 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN daily_avg < 150 OR daily_avg IS NULL THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM public.multimodal_points
            WHERE geom && tile_bbox_4326
            GROUP BY floor(ST_X(geom) / grid_size), floor(ST_Y(geom) / grid_size)
            HAVING count(*) >= 1
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;

-- Create WHCA filtered clustered function
-- Uses daily_avg (average of all models) for alert level calculation
DROP FUNCTION IF EXISTS public.multimodal_points_clustered_whca(integer, integer, integer, integer);

CREATE OR REPLACE FUNCTION public.multimodal_points_clustered_whca(z integer, x integer, y integer, cluster_zoom integer DEFAULT 10)
 RETURNS bytea
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
    grid_size float;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);
    grid_size := 40.0 / power(2, z);

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'public.multimodal_points_clustered', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id, point_id, zone, gridcode, has_data, admin_name,
                data_date::text as data_date, forecast_date::text as forecast_date,
                daily_avg, daily_max, daily_min,
                geosfm, floodproof, mike_hydro_rfe, mike_hydro_chirp, mike_hydro_imerg,
                forecasts_json::text as forecasts_json,
                CASE WHEN daily_avg >= 450 THEN 'emergency' WHEN daily_avg >= 300 THEN 'alarm' WHEN daily_avg >= 150 THEN 'warning' ELSE 'normal' END as alert_level,
                CASE WHEN daily_avg >= 450 THEN 4 WHEN daily_avg >= 300 THEN 3 WHEN daily_avg >= 150 THEN 2 ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM public.multimodal_points
            WHERE geom && tile_bbox_4326
              AND (admin_name LIKE 'UG%' OR admin_name LIKE 'RW%' OR admin_name LIKE 'SS%' OR admin_name LIKE 'ET%' OR admin_name LIKE 'SD%')
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'public.multimodal_points_clustered', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(id) as id, count(*) as point_count, max(daily_max) as daily_max,
                avg(daily_avg)::numeric(10,2) as daily_avg, min(data_date)::text as data_date,
                CASE WHEN max(daily_avg) >= 450 THEN 'emergency' WHEN max(daily_avg) >= 300 THEN 'alarm' WHEN max(daily_avg) >= 150 THEN 'warning' ELSE 'normal' END as alert_level,
                CASE WHEN max(daily_avg) >= 450 THEN 4 WHEN max(daily_avg) >= 300 THEN 3 WHEN max(daily_avg) >= 150 THEN 2 ELSE 1 END as alert_priority,
                sum(CASE WHEN daily_avg >= 450 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN daily_avg >= 300 AND daily_avg < 450 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN daily_avg >= 150 AND daily_avg < 300 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN daily_avg < 150 OR daily_avg IS NULL THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM public.multimodal_points
            WHERE geom && tile_bbox_4326
              AND (admin_name LIKE 'UG%' OR admin_name LIKE 'RW%' OR admin_name LIKE 'SS%' OR admin_name LIKE 'ET%' OR admin_name LIKE 'SD%')
            GROUP BY floor(ST_X(geom) / grid_size), floor(ST_Y(geom) / grid_size)
            HAVING count(*) >= 1
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.multimodal_points_clustered(integer, integer, integer, integer) TO PUBLIC;
GRANT EXECUTE ON FUNCTION public.multimodal_points_clustered_whca(integer, integer, integer, integer) TO PUBLIC;

-- Add comments for pg_tileserv
COMMENT ON FUNCTION public.multimodal_points_clustered IS 'Clustered multimodal forecast points with alert levels based on daily_avg. Thresholds: Warning >= 150, Alarm >= 300, Emergency >= 450 m³/s. cluster_zoom param controls when clustering stops (default 10).';
COMMENT ON FUNCTION public.multimodal_points_clustered_whca IS 'WHCA filtered clustered multimodal forecast points (Uganda, Rwanda, South Sudan, Ethiopia, Sudan). Uses daily_avg for alert levels.';
            """,
            reverse_sql="""
DROP FUNCTION IF EXISTS public.multimodal_points_clustered(integer, integer, integer, integer);
DROP FUNCTION IF EXISTS public.multimodal_points_clustered_whca(integer, integer, integer, integer);
            """,
        ),
    ]
