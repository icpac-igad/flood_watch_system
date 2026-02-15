from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0046_create_wrf_total_rainfall_tiles_function"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE OR REPLACE FUNCTION gha.resolve_admin_extent_geom(
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    clip_geom geometry;
BEGIN
    IF (country_name IS NULL OR country_name = '')
       AND (region_name IS NULL OR region_name = '')
       AND (district_name IS NULL OR district_name = '') THEN
        SELECT geom INTO clip_geom
        FROM gha.admin_extent_cache
        WHERE id = TRUE
        LIMIT 1;

        IF clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
            PERFORM gha.refresh_admin_extent_cache();
            SELECT geom INTO clip_geom
            FROM gha.admin_extent_cache
            WHERE id = TRUE
            LIMIT 1;
        END IF;

        RETURN clip_geom;
    END IF;

    IF district_name IS NOT NULL AND district_name <> '' THEN
        SELECT ST_UnaryUnion(ST_Collect(geom)) INTO clip_geom
        FROM gha.admin2
        WHERE name_2 = district_name
          AND (region_name IS NULL OR region_name = '' OR name_1 = region_name)
          AND (country_name IS NULL OR country_name = '' OR country = country_name);
    ELSIF region_name IS NOT NULL AND region_name <> '' THEN
        SELECT ST_UnaryUnion(ST_Collect(geom)) INTO clip_geom
        FROM gha.admin1
        WHERE name_1 = region_name
          AND (country_name IS NULL OR country_name = '' OR country = country_name);
    ELSIF country_name IS NOT NULL AND country_name <> '' THEN
        SELECT ST_UnaryUnion(ST_Collect(geom)) INTO clip_geom
        FROM gha.admin0
        WHERE country = country_name;
    END IF;

    -- Always enforce ICPAC extent even when no country/region/district filter is passed.
    IF clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
        SELECT geom INTO clip_geom
        FROM gha.admin_extent_cache
        WHERE id = TRUE
        LIMIT 1;

        IF clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
            PERFORM gha.refresh_admin_extent_cache();
            SELECT geom INTO clip_geom
            FROM gha.admin_extent_cache
            WHERE id = TRUE
            LIMIT 1;
        END IF;
    END IF;

    RETURN clip_geom;
END;
$function$;

CREATE TABLE IF NOT EXISTS gha.admin_extent_cache (
    id boolean PRIMARY KEY DEFAULT TRUE CHECK (id),
    geom geometry(Geometry, 4326),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION gha.refresh_admin_extent_cache()
RETURNS void
LANGUAGE plpgsql
VOLATILE
PARALLEL UNSAFE
AS $function$
DECLARE
    merged_geom geometry;
BEGIN
    SELECT ST_Multi(ST_UnaryUnion(ST_Collect(geom))) INTO merged_geom
    FROM gha.admin0;

    INSERT INTO gha.admin_extent_cache(id, geom, updated_at)
    VALUES (TRUE, merged_geom, now())
    ON CONFLICT (id) DO UPDATE
    SET geom = EXCLUDED.geom,
        updated_at = EXCLUDED.updated_at;
END;
$function$;

SELECT gha.refresh_admin_extent_cache();

CREATE OR REPLACE FUNCTION gha.clip_geom_to_admin_extent(
    input_geom geometry,
    clip_geom geometry
)
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    geom_4326 geometry;
    clip_4326 geometry;
    geom_valid geometry;
    clip_valid geometry;
    clipped geometry;
BEGIN
    IF input_geom IS NULL OR clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
        RETURN NULL;
    END IF;

    geom_4326 := CASE
        WHEN ST_SRID(input_geom) = 4326 THEN input_geom
        WHEN ST_SRID(input_geom) = 0 THEN ST_SetSRID(input_geom, 4326)
        ELSE ST_Transform(input_geom, 4326)
    END;

    clip_4326 := CASE
        WHEN ST_SRID(clip_geom) = 4326 THEN clip_geom
        WHEN ST_SRID(clip_geom) = 0 THEN ST_SetSRID(clip_geom, 4326)
        ELSE ST_Transform(clip_geom, 4326)
    END;

    IF NOT ST_Intersects(geom_4326, clip_4326) THEN
        RETURN NULL;
    END IF;

    geom_valid := CASE WHEN ST_IsValid(geom_4326) THEN geom_4326 ELSE ST_MakeValid(geom_4326) END;
    clip_valid := CASE WHEN ST_IsValid(clip_4326) THEN clip_4326 ELSE ST_MakeValid(clip_4326) END;

    clipped := ST_Intersection(geom_valid, clip_valid);
    IF clipped IS NULL OR ST_IsEmpty(clipped) THEN
        RETURN NULL;
    END IF;

    RETURN ST_MakeValid(clipped);
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$function$;

CREATE OR REPLACE FUNCTION gha.clip_geom_to_admin_extent(
    input_geom geometry,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    clip_geom geometry;
BEGIN
    clip_geom := gha.resolve_admin_extent_geom(country_name, region_name, district_name);
    RETURN gha.clip_geom_to_admin_extent(input_geom, clip_geom);
END;
$function$;

CREATE OR REPLACE FUNCTION gha.clip_to_admin(
    z integer,
    x integer,
    y integer,
    table_name text,
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
    filter_geom geometry;
    effective_clip_geom geometry;
    schema_name text;
    relation_name text;
    layer_name text;
    sql_query text;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    schema_name := split_part(table_name, '.', 1);
    relation_name := split_part(table_name, '.', 2);

    IF schema_name = '' OR relation_name = '' THEN
        RAISE EXCEPTION 'table_name must be schema-qualified (schema.table), got: %', table_name;
    END IF;

    layer_name := format('%s.%s', schema_name, relation_name);
    filter_geom := gha.resolve_admin_extent_geom(country_name, region_name, district_name);
    effective_clip_geom := gha.clip_geom_to_admin_extent(tile_bbox_4326, filter_geom);

    IF effective_clip_geom IS NULL OR ST_IsEmpty(effective_clip_geom) THEN
        RETURN ''::bytea;
    END IF;

    sql_query := format(
        'SELECT ST_AsMVT(tile, %L, 4096, ''mvt_geom'')
         FROM (
             SELECT
                 t.*,
                 ST_AsMVTGeom(
                     ST_Transform(c.clipped_geom, 3857),
                     $1,
                     4096,
                     64,
                     true
                 ) AS mvt_geom
             FROM %I.%I t
             CROSS JOIN LATERAL (
                 SELECT gha.clip_geom_to_admin_extent(t.geom, $3) AS clipped_geom
             ) c
             WHERE t.geom && $3
               AND c.clipped_geom IS NOT NULL
               AND c.clipped_geom && $2
         ) AS tile
         WHERE tile.mvt_geom IS NOT NULL',
        layer_name,
        schema_name,
        relation_name
    );

    EXECUTE sql_query INTO mvt USING tile_bbox_3857, tile_bbox_4326, effective_clip_geom;
    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.resolve_admin_extent_geom(text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.refresh_admin_extent_cache() TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.clip_geom_to_admin_extent(geometry, geometry) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.clip_geom_to_admin_extent(geometry, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.clip_to_admin(integer, integer, integer, text, text, text, text) TO PUBLIC;

COMMENT ON FUNCTION gha.resolve_admin_extent_geom(text, text, text)
IS 'Resolves admin clipping geometry. Defaults to union of gha.admin0 when no filters are provided.';
COMMENT ON FUNCTION gha.refresh_admin_extent_cache()
IS 'Refreshes cached ICPAC admin extent geometry used for fast default clipping.';
COMMENT ON FUNCTION gha.clip_geom_to_admin_extent(geometry, geometry)
IS 'Clips any geometry to the provided admin extent geometry and returns result in EPSG:4326.';
COMMENT ON FUNCTION gha.clip_geom_to_admin_extent(geometry, text, text, text)
IS 'Clips any geometry to the selected country/region/district extent. Defaults to full admin0 extent.';
COMMENT ON FUNCTION gha.clip_to_admin(integer, integer, integer, text, text, text, text)
IS 'Generic MVT clipper. Always constrains output to ICPAC admin extent (admin0 by default), with optional admin1/admin2 narrowing.';
            """,
            reverse_sql="""
DROP FUNCTION IF EXISTS gha.clip_to_admin(integer, integer, integer, text, text, text, text);
DROP FUNCTION IF EXISTS gha.clip_geom_to_admin_extent(geometry, text, text, text);
DROP FUNCTION IF EXISTS gha.clip_geom_to_admin_extent(geometry, geometry);
DROP FUNCTION IF EXISTS gha.refresh_admin_extent_cache();
DROP FUNCTION IF EXISTS gha.resolve_admin_extent_geom(text, text, text);
DROP TABLE IF EXISTS gha.admin_extent_cache;
            """,
        ),
    ]
