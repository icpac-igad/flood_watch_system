-- Generic raster clipping/masking functions for pg_tileserv
-- Run with: docker exec -i eafw-pgdb psql -U geomanager -d geomanager_web -f /tmp/create_raster_functions.sql

CREATE EXTENSION IF NOT EXISTS postgis_raster SCHEMA public CASCADE;

CREATE TABLE IF NOT EXISTS gha.population_raster (
    rid SERIAL PRIMARY KEY,
    rast raster NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_population_raster_rast_st_convexhull
    ON gha.population_raster USING GIST (ST_ConvexHull(rast));

-- ============================================================
-- Generic function: clip any raster to admin boundary as pixel polygons
-- ============================================================

DROP FUNCTION IF EXISTS gha.raster_clipped(integer, integer, integer, text, text, text, text, double precision);

CREATE OR REPLACE FUNCTION gha.raster_clipped(
    z integer,
    x integer,
    y integer,
    raster_table text DEFAULT 'gha.population_raster',
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL,
    min_value double precision DEFAULT 1
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
    clip_geom geometry;
    schema_name text;
    relation_name text;
    sql_query text;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    schema_name := split_part(raster_table, '.', 1);
    relation_name := split_part(raster_table, '.', 2);
    IF relation_name = '' THEN
        schema_name := 'gha';
        relation_name := split_part(raster_table, '.', 1);
    END IF;

    admin_geom := gha.resolve_admin_extent_geom(country_name, region_name, district_name);
    clip_geom := gha.clip_geom_to_admin_extent(tile_bbox_4326, admin_geom);

    IF clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
        RETURN ''::bytea;
    END IF;

    sql_query := format(
        'SELECT ST_AsMVT(tile, ''gha.raster_clipped'', 4096, ''mvt_geom'')
         FROM (
             SELECT
                 pix.val::double precision AS value,
                 ST_AsMVTGeom(
                     ST_Transform(pix.geom, 3857),
                     $1, 4096, 64, true
                 ) AS mvt_geom
             FROM %I.%I r,
             LATERAL ST_PixelAsPolygons(
                 ST_Clip(r.rast, 1, $2, -1, true),
                 1, false
             ) AS pix
             WHERE ST_Intersects(ST_ConvexHull(r.rast), $2)
               AND pix.val IS NOT NULL
               AND pix.val >= $3
         ) AS tile
         WHERE tile.mvt_geom IS NOT NULL',
        schema_name, relation_name
    );

    EXECUTE sql_query INTO mvt USING tile_bbox_3857, clip_geom, min_value;
    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

-- ============================================================
-- Generic function: summarize any raster within admin polygons
-- ============================================================

DROP FUNCTION IF EXISTS gha.raster_summary(integer, integer, integer, text, text, text, text, double precision);

CREATE OR REPLACE FUNCTION gha.raster_summary(
    z integer,
    x integer,
    y integer,
    raster_table text DEFAULT 'gha.population_raster',
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL,
    min_value double precision DEFAULT 0
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
    schema_name text;
    relation_name text;
    sql_query text;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    schema_name := split_part(raster_table, '.', 1);
    relation_name := split_part(raster_table, '.', 2);
    IF relation_name = '' THEN
        schema_name := 'gha';
        relation_name := split_part(raster_table, '.', 1);
    END IF;

    IF district_name IS NOT NULL AND district_name <> '' THEN
        sql_query := format(
            'SELECT ST_AsMVT(tile, ''gha.raster_summary'', 4096, ''mvt_geom'')
             FROM (
                 SELECT
                     a.id, a.country, a.name_1 AS region, a.name_2 AS district,
                     ''2'' AS admin_level,
                     COALESCE(agg.total, 0)::double precision AS total,
                     COALESCE(agg.mean, 0)::numeric(10,1) AS mean,
                     COALESCE(agg.max_val, 0)::double precision AS max_val,
                     COALESCE(agg.cell_count, 0)::integer AS cell_count,
                     ST_AsMVTGeom(ST_Transform(a.geom, 3857), $1, 4096, 64, true) AS mvt_geom
                 FROM gha.admin2 a
                 LEFT JOIN LATERAL (
                     SELECT SUM((stats).sum) AS total, AVG((stats).mean) AS mean,
                            MAX((stats).max) AS max_val, SUM((stats).count) AS cell_count
                     FROM (
                         SELECT ST_SummaryStats(ST_Clip(r.rast, 1, a.geom, -1, true)) AS stats
                         FROM %I.%I r WHERE ST_Intersects(ST_ConvexHull(r.rast), a.geom)
                     ) s
                 ) agg ON true
                 WHERE a.geom && $2 AND a.name_2 = $3
                   AND ($4 IS NULL OR $4 = '''' OR a.name_1 = $4)
                   AND ($5 IS NULL OR $5 = '''' OR a.country = $5)
                   AND COALESCE(agg.total, 0) >= $6
             ) AS tile WHERE tile.mvt_geom IS NOT NULL',
            schema_name, relation_name
        );
        EXECUTE sql_query INTO mvt
            USING tile_bbox_3857, tile_bbox_4326, district_name, region_name, country_name, min_value;

    ELSIF region_name IS NOT NULL AND region_name <> '' THEN
        sql_query := format(
            'SELECT ST_AsMVT(tile, ''gha.raster_summary'', 4096, ''mvt_geom'')
             FROM (
                 SELECT
                     a.id, a.country, a.name_1 AS region, NULL::text AS district,
                     ''1'' AS admin_level,
                     COALESCE(agg.total, 0)::double precision AS total,
                     COALESCE(agg.mean, 0)::numeric(10,1) AS mean,
                     COALESCE(agg.max_val, 0)::double precision AS max_val,
                     COALESCE(agg.cell_count, 0)::integer AS cell_count,
                     ST_AsMVTGeom(ST_Transform(a.geom, 3857), $1, 4096, 64, true) AS mvt_geom
                 FROM gha.admin1 a
                 LEFT JOIN LATERAL (
                     SELECT SUM((stats).sum) AS total, AVG((stats).mean) AS mean,
                            MAX((stats).max) AS max_val, SUM((stats).count) AS cell_count
                     FROM (
                         SELECT ST_SummaryStats(ST_Clip(r.rast, 1, a.geom, -1, true)) AS stats
                         FROM %I.%I r WHERE ST_Intersects(ST_ConvexHull(r.rast), a.geom)
                     ) s
                 ) agg ON true
                 WHERE a.geom && $2 AND a.name_1 = $3
                   AND ($4 IS NULL OR $4 = '''' OR a.country = $4)
                   AND COALESCE(agg.total, 0) >= $5
             ) AS tile WHERE tile.mvt_geom IS NOT NULL',
            schema_name, relation_name
        );
        EXECUTE sql_query INTO mvt
            USING tile_bbox_3857, tile_bbox_4326, region_name, country_name, min_value;

    ELSE
        sql_query := format(
            'SELECT ST_AsMVT(tile, ''gha.raster_summary'', 4096, ''mvt_geom'')
             FROM (
                 SELECT
                     a.id, a.country, NULL::text AS region, NULL::text AS district,
                     ''0'' AS admin_level,
                     COALESCE(agg.total, 0)::double precision AS total,
                     COALESCE(agg.mean, 0)::numeric(10,1) AS mean,
                     COALESCE(agg.max_val, 0)::double precision AS max_val,
                     COALESCE(agg.cell_count, 0)::integer AS cell_count,
                     ST_AsMVTGeom(ST_Transform(a.geom, 3857), $1, 4096, 64, true) AS mvt_geom
                 FROM gha.admin0 a
                 LEFT JOIN LATERAL (
                     SELECT SUM((stats).sum) AS total, AVG((stats).mean) AS mean,
                            MAX((stats).max) AS max_val, SUM((stats).count) AS cell_count
                     FROM (
                         SELECT ST_SummaryStats(ST_Clip(r.rast, 1, a.geom, -1, true)) AS stats
                         FROM %I.%I r WHERE ST_Intersects(ST_ConvexHull(r.rast), a.geom)
                     ) s
                 ) agg ON true
                 WHERE a.geom && $2
                   AND ($3 IS NULL OR $3 = '''' OR a.country = $3)
                   AND COALESCE(agg.total, 0) >= $4
             ) AS tile WHERE tile.mvt_geom IS NOT NULL',
            schema_name, relation_name
        );
        EXECUTE sql_query INTO mvt
            USING tile_bbox_3857, tile_bbox_4326, country_name, min_value;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

-- Grant execute to PUBLIC for pg_tileserv access
GRANT EXECUTE ON FUNCTION gha.raster_clipped(integer, integer, integer, text, text, text, text, double precision) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.raster_summary(integer, integer, integer, text, text, text, text, double precision) TO PUBLIC;

COMMENT ON FUNCTION gha.raster_clipped IS 'Generic raster clipper. Clips any raster table to admin boundaries and returns pixel polygons as MVT. raster_table: schema-qualified table (default gha.population_raster). Filter by country/region/district.';
COMMENT ON FUNCTION gha.raster_summary IS 'Generic raster summary per admin polygon. Auto-selects admin level: district → admin2, region → admin1, default → admin0. Returns total, mean, max_val, cell_count.';
