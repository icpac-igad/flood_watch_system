# Generated migration to create admin filtering functions for pg_tileserv
# - gha.admin_clipped: Admin boundary tiles filtered by country/region/district
# - public.multimodal_points_by_admin: Multimodal points filtered by admin area

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0024_add_category_description'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
-- =============================================================================
-- Create gha.admin_clipped function for pg_tileserv
-- Returns admin boundary tiles filtered by country, region, or district
-- admin_level: 0=country, 1=region, 2=district

DROP FUNCTION IF EXISTS gha.admin_clipped(integer, integer, integer, integer, text, text, text);

CREATE OR REPLACE FUNCTION gha.admin_clipped(
    z integer,
    x integer,
    y integer,
    admin_level integer DEFAULT 0,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
BEGIN
    -- Calculate tile bounding box
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    IF admin_level = 0 THEN
        -- Admin Level 0: Countries
        SELECT ST_AsMVT(tile, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                country,
                ST_AsMVTGeom(
                    ST_Transform(geom, 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin0
            WHERE geom && tile_bbox_4326
              AND (country_name IS NULL OR country = country_name)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 1 THEN
        -- Admin Level 1: Regions/Provinces
        SELECT ST_AsMVT(tile, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                country,
                name_1 as region,
                ST_AsMVTGeom(
                    ST_Transform(geom, 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin1
            WHERE geom && tile_bbox_4326
              AND (country_name IS NULL OR country = country_name)
              AND (region_name IS NULL OR name_1 = region_name)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 2 THEN
        -- Admin Level 2: Districts
        SELECT ST_AsMVT(tile, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                country,
                name_1 as region,
                name_2 as district,
                ST_AsMVTGeom(
                    ST_Transform(geom, 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin2
            WHERE geom && tile_bbox_4326
              AND (country_name IS NULL OR country = country_name)
              AND (region_name IS NULL OR name_1 = region_name)
              AND (district_name IS NULL OR name_2 = district_name)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSE
        -- Default to admin0 if invalid admin_level
        SELECT ST_AsMVT(tile, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                country,
                ST_AsMVTGeom(
                    ST_Transform(geom, 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin0
            WHERE geom && tile_bbox_4326
              AND (country_name IS NULL OR country = country_name)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION gha.admin_clipped(integer, integer, integer, integer, text, text, text) TO PUBLIC;

-- Add comment for pg_tileserv
COMMENT ON FUNCTION gha.admin_clipped IS 'Admin boundary tiles filtered by country/region/district. Parameters: admin_level (0=country, 1=region, 2=district), country_name, region_name, district_name.';

-- =============================================================================
-- Create public.multimodal_points_by_admin function for pg_tileserv
-- Filters multimodal forecast points by admin boundaries using spatial intersection
-- =============================================================================

DROP FUNCTION IF EXISTS public.multimodal_points_by_admin(integer, integer, integer, integer, text, text, text);

CREATE OR REPLACE FUNCTION public.multimodal_points_by_admin(
    z integer,
    x integer,
    y integer,
    cluster_zoom integer DEFAULT 10,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
AS $func$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
    grid_size float;
    admin_geom geometry;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);
    grid_size := 40.0 / power(2, z);

    -- Get admin boundary geometry for spatial filtering
    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin2
        WHERE name_2 = district_name
        AND (region_name IS NULL OR name_1 = region_name)
        AND (country_name IS NULL OR country = country_name)
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin1
        WHERE name_1 = region_name
        AND (country_name IS NULL OR country = country_name)
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin0
        WHERE country = country_name
        LIMIT 1;
    END IF;

    IF z >= cluster_zoom THEN
        SELECT ST_AsMVT(tile, 'public.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                m.id, m.point_id, m.zone, m.gridcode, m.has_data, m.admin_name,
                m.data_date::text as data_date,
                m.forecast_date::text as forecast_date,
                m.daily_avg, m.daily_max, m.daily_min,
                m.geosfm, m.floodproof, m.mike_hydro_rfe, m.mike_hydro_chirp, m.mike_hydro_imerg,
                m.forecasts_json::text as forecasts_json,
                CASE WHEN m.daily_avg >= 450 THEN 'emergency' WHEN m.daily_avg >= 300 THEN 'alarm' WHEN m.daily_avg >= 150 THEN 'warning' ELSE 'normal' END as alert_level,
                CASE WHEN m.daily_avg >= 450 THEN 4 WHEN m.daily_avg >= 300 THEN 3 WHEN m.daily_avg >= 150 THEN 2 ELSE 1 END as alert_priority,
                1 as point_count,
                ST_AsMVTGeom(ST_Transform(m.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM public.multimodal_points m
            WHERE m.geom && tile_bbox_4326
              AND (admin_geom IS NULL OR ST_Intersects(m.geom, admin_geom))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'public.multimodal_points_by_admin', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                min(m.id) as id, count(*) as point_count, max(m.daily_max) as daily_max,
                avg(m.daily_avg)::numeric(10,2) as daily_avg, min(m.data_date)::text as data_date,
                CASE WHEN max(m.daily_avg) >= 450 THEN 'emergency' WHEN max(m.daily_avg) >= 300 THEN 'alarm' WHEN max(m.daily_avg) >= 150 THEN 'warning' ELSE 'normal' END as alert_level,
                CASE WHEN max(m.daily_avg) >= 450 THEN 4 WHEN max(m.daily_avg) >= 300 THEN 3 WHEN max(m.daily_avg) >= 150 THEN 2 ELSE 1 END as alert_priority,
                sum(CASE WHEN m.daily_avg >= 450 THEN 1 ELSE 0 END)::integer as emergency_count,
                sum(CASE WHEN m.daily_avg >= 300 AND m.daily_avg < 450 THEN 1 ELSE 0 END)::integer as alarm_count,
                sum(CASE WHEN m.daily_avg >= 150 AND m.daily_avg < 300 THEN 1 ELSE 0 END)::integer as warning_count,
                sum(CASE WHEN m.daily_avg < 150 OR m.daily_avg IS NULL THEN 1 ELSE 0 END)::integer as normal_count,
                false as has_data,
                ST_AsMVTGeom(ST_Transform(ST_Centroid(ST_Collect(m.geom)), 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM public.multimodal_points m
            WHERE m.geom && tile_bbox_4326
              AND (admin_geom IS NULL OR ST_Intersects(m.geom, admin_geom))
            GROUP BY floor(ST_X(m.geom) / grid_size), floor(ST_Y(m.geom) / grid_size)
            HAVING count(*) >= 1
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$func$;

GRANT EXECUTE ON FUNCTION public.multimodal_points_by_admin(integer, integer, integer, integer, text, text, text) TO PUBLIC;
COMMENT ON FUNCTION public.multimodal_points_by_admin IS 'Multimodal points filtered by admin boundary using spatial intersection.';
            """,
            reverse_sql="""
DROP FUNCTION IF EXISTS gha.admin_clipped(integer, integer, integer, integer, text, text, text);
DROP FUNCTION IF EXISTS public.multimodal_points_by_admin(integer, integer, integer, integer, text, text, text);
            """,
        ),
    ]
