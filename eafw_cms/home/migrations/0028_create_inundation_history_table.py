# Generated migration to create inundation history table and pg_tileserv functions
# - climate.inundation_history_tiles: Stores raw GeoJSON tiles from Google
# - climate.inundation_history_clipped: pg_tileserv function that clips to admin boundaries

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0027_add_hero_question_field'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
-- =============================================================================
-- Create climate schema if not exists
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS climate;

-- =============================================================================
-- Create inundation_history_tiles table
-- Stores raw GeoJSON tiles from Google's flood-forecasting bucket
-- =============================================================================

CREATE TABLE IF NOT EXISTS climate.inundation_history_tiles (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    min_lat DOUBLE PRECISION NOT NULL,
    min_lon DOUBLE PRECISION NOT NULL,
    max_lat DOUBLE PRECISION NOT NULL,
    max_lon DOUBLE PRECISION NOT NULL,
    geojson_data JSONB NOT NULL,
    feature_count INTEGER DEFAULT 0,
    high_risk_count INTEGER DEFAULT 0,
    medium_risk_count INTEGER DEFAULT 0,
    low_risk_count INTEGER DEFAULT 0,
    source VARCHAR(50) DEFAULT 'google_gcs',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for spatial queries
CREATE INDEX IF NOT EXISTS idx_inundation_tiles_bounds
    ON climate.inundation_history_tiles (min_lat, min_lon, max_lat, max_lon);

-- =============================================================================
-- Create materialized view for inundation geometries (for faster tile serving)
-- Extracts polygons from GeoJSON and stores as PostGIS geometries
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS climate.inundation_history_geom AS
SELECT
    t.id as tile_id,
    t.filename,
    (f->>'id')::integer as feature_id,
    f->'properties'->>'layer' as risk_level,
    ST_SetSRID(ST_GeomFromGeoJSON(f->>'geometry'), 4326) as geom
FROM climate.inundation_history_tiles t,
     LATERAL jsonb_array_elements(t.geojson_data->'features') AS f
WHERE f->>'geometry' IS NOT NULL;

-- Create spatial index
CREATE INDEX IF NOT EXISTS idx_inundation_geom_gist
    ON climate.inundation_history_geom USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_inundation_geom_risk
    ON climate.inundation_history_geom (risk_level);

-- =============================================================================
-- Create pg_tileserv function: climate.inundation_history_clipped
-- Returns inundation history tiles clipped to admin boundaries
-- Supports filtering by risk_level, country, region, district
-- =============================================================================

DROP FUNCTION IF EXISTS climate.inundation_history_clipped(integer, integer, integer, text, text, text, text);

CREATE OR REPLACE FUNCTION climate.inundation_history_clipped(
    z integer,
    x integer,
    y integer,
    risk_level text DEFAULT NULL,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
    admin_geom geometry;
BEGIN
    -- Calculate tile bounding box
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    -- Get admin boundary geometry for clipping
    IF district_name IS NOT NULL AND district_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin2
        WHERE name_2 = district_name
        AND (region_name IS NULL OR region_name = '' OR name_1 = region_name)
        AND (country_name IS NULL OR country_name = '' OR country = country_name)
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin1
        WHERE name_1 = region_name
        AND (country_name IS NULL OR country_name = '' OR country = country_name)
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name != '' THEN
        SELECT geom INTO admin_geom FROM gha.admin0
        WHERE country = country_name
        LIMIT 1;
    END IF;

    -- Build MVT with optional admin clipping
    IF admin_geom IS NOT NULL THEN
        -- Clip to admin boundary
        SELECT ST_AsMVT(tile, 'climate.inundation_history_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                i.feature_id,
                i.risk_level,
                CASE i.risk_level
                    WHEN 'High_risk' THEN 3
                    WHEN 'Medium_risk' THEN 2
                    WHEN 'Low_risk' THEN 1
                    ELSE 0
                END as risk_priority,
                ST_AsMVTGeom(
                    ST_Transform(ST_Intersection(i.geom, admin_geom), 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM climate.inundation_history_geom i
            WHERE i.geom && tile_bbox_4326
              AND ST_Intersects(i.geom, admin_geom)
              AND (risk_level IS NULL OR risk_level = '' OR i.risk_level = risk_level)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        -- No admin filter - return all features in tile
        SELECT ST_AsMVT(tile, 'climate.inundation_history_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                i.feature_id,
                i.risk_level,
                CASE i.risk_level
                    WHEN 'High_risk' THEN 3
                    WHEN 'Medium_risk' THEN 2
                    WHEN 'Low_risk' THEN 1
                    ELSE 0
                END as risk_priority,
                ST_AsMVTGeom(
                    ST_Transform(i.geom, 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM climate.inundation_history_geom i
            WHERE i.geom && tile_bbox_4326
              AND (risk_level IS NULL OR risk_level = '' OR i.risk_level = risk_level)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, '');
END;
$function$;

-- Grant permissions
GRANT USAGE ON SCHEMA climate TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA climate TO PUBLIC;
GRANT EXECUTE ON FUNCTION climate.inundation_history_clipped(integer, integer, integer, text, text, text, text) TO PUBLIC;

-- Add comment for pg_tileserv discovery
COMMENT ON FUNCTION climate.inundation_history_clipped IS 'Historical flood inundation areas from Google (1999-2020). Filter by risk_level (High_risk, Medium_risk, Low_risk) and admin boundaries (country_name, region_name, district_name). Data clipped to selected admin area.';

-- =============================================================================
-- Create refresh function for materialized view
-- =============================================================================

CREATE OR REPLACE FUNCTION climate.refresh_inundation_geom()
RETURNS void
LANGUAGE plpgsql
AS $func$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY climate.inundation_history_geom;
END;
$func$;

COMMENT ON FUNCTION climate.refresh_inundation_geom IS 'Refreshes the inundation geometry materialized view. Call after ingesting new tiles.';
            """,
            reverse_sql="""
DROP FUNCTION IF EXISTS climate.refresh_inundation_geom();
DROP FUNCTION IF EXISTS climate.inundation_history_clipped(integer, integer, integer, text, text, text, text);
DROP MATERIALIZED VIEW IF EXISTS climate.inundation_history_geom;
DROP TABLE IF EXISTS climate.inundation_history_tiles;
DROP SCHEMA IF EXISTS climate CASCADE;
            """,
        ),
    ]
