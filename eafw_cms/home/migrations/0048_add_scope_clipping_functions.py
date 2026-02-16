from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0047_enforce_admin_extent_clipping"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE OR REPLACE FUNCTION gha.resolve_scope_extent_geom(
    scope_mode text DEFAULT NULL,
    project_countries text DEFAULT NULL,
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
    normalized_scope text := lower(COALESCE(NULLIF(trim(scope_mode), ''), 'all'));
    scope_geom geometry;
    admin_geom geometry;
    has_admin_filter boolean := (
        (country_name IS NOT NULL AND trim(country_name) <> '')
        OR (region_name IS NOT NULL AND trim(region_name) <> '')
        OR (district_name IS NOT NULL AND trim(district_name) <> '')
    );
    countries_arr text[];
    whca_countries text[] := ARRAY['Sudan', 'South Sudan', 'Uganda', 'Ethiopia', 'Rwanda'];
BEGIN
    admin_geom := gha.resolve_admin_extent_geom(country_name, region_name, district_name);

    IF normalized_scope = 'all' AND (project_countries IS NULL OR trim(project_countries) = '') THEN
        RETURN admin_geom;
    END IF;

    IF normalized_scope = 'whca' THEN
        SELECT ST_Multi(ST_UnaryUnion(ST_Collect(geom))) INTO scope_geom
        FROM gha.admin0
        WHERE country = ANY(whca_countries);
    ELSIF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        countries_arr := regexp_split_to_array(project_countries, '\\s*,\\s*');
        SELECT ST_Multi(ST_UnaryUnion(ST_Collect(geom))) INTO scope_geom
        FROM gha.admin0
        WHERE country = ANY(countries_arr);
    ELSE
        scope_geom := gha.resolve_admin_extent_geom(NULL, NULL, NULL);
    END IF;

    IF scope_geom IS NULL OR ST_IsEmpty(scope_geom) THEN
        RETURN admin_geom;
    END IF;

    IF NOT has_admin_filter THEN
        RETURN ST_Multi(ST_MakeValid(scope_geom));
    END IF;

    IF admin_geom IS NULL OR ST_IsEmpty(admin_geom) THEN
        RETURN NULL;
    END IF;

    IF normalized_scope = 'whca'
       AND country_name IS NOT NULL
       AND trim(country_name) <> ''
       AND NOT (country_name = ANY(whca_countries)) THEN
        RETURN NULL;
    END IF;

    IF project_countries IS NOT NULL
       AND trim(project_countries) <> ''
       AND country_name IS NOT NULL
       AND trim(country_name) <> ''
       AND NOT (country_name = ANY(countries_arr)) THEN
        RETURN NULL;
    END IF;

    IF ST_Within(admin_geom, scope_geom) THEN
        RETURN ST_Multi(ST_MakeValid(admin_geom));
    END IF;

    IF NOT ST_Intersects(admin_geom, scope_geom) THEN
        RETURN NULL;
    END IF;

    RETURN ST_Multi(ST_MakeValid(ST_Intersection(admin_geom, scope_geom)));
END;
$function$;

CREATE OR REPLACE FUNCTION gha.clip_to_scope(
    z integer,
    x integer,
    y integer,
    table_name text,
    scope_mode text DEFAULT NULL,
    project_countries text DEFAULT NULL,
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
    filter_geom := gha.resolve_scope_extent_geom(
        scope_mode,
        project_countries,
        country_name,
        region_name,
        district_name
    );
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

DROP FUNCTION IF EXISTS gha.admin_whca(integer, integer, integer, integer);
CREATE FUNCTION gha.admin_whca(
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
PARALLEL SAFE
AS $function$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
    whca_countries text[] := ARRAY['Sudan', 'South Sudan', 'Uganda', 'Ethiopia', 'Rwanda'];
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    IF admin_level = 1 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid, a.gid_0, a.country, a.gid_1,
                a.name_1 AS region, a.type_1, a.shape_area,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && tile_bbox_4326
              AND (country_name IS NULL OR country_name = '' OR LOWER(a.country) = LOWER(country_name))
              AND (region_name IS NULL OR region_name = '' OR LOWER(a.name_1) = LOWER(region_name))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 2 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid, a.gid_0, a.country, a.gid_1,
                a.name_1 AS region, a.gid_2, a.name_2 AS district, a.type_2,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin2 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && tile_bbox_4326
              AND (country_name IS NULL OR country_name = '' OR LOWER(a.country) = LOWER(country_name))
              AND (region_name IS NULL OR region_name = '' OR LOWER(a.name_1) = LOWER(region_name))
              AND (district_name IS NULL OR district_name = '' OR LOWER(a.name_2) = LOWER(district_name))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSE
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid, a.gid_0, a.country, a.shape_area,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin0 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && tile_bbox_4326
              AND (country_name IS NULL OR country_name = '' OR LOWER(a.country) = LOWER(country_name))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.resolve_scope_extent_geom(text, text, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.clip_to_scope(integer, integer, integer, text, text, text, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.admin_whca(integer, integer, integer, integer, text, text, text) TO PUBLIC;

COMMENT ON FUNCTION gha.resolve_scope_extent_geom(text, text, text, text, text)
IS 'Resolves clipping geometry for scope (all/project/whca) and optional admin drill-down filters.';
COMMENT ON FUNCTION gha.clip_to_scope(integer, integer, integer, text, text, text, text, text, text)
IS 'Generic pg_tileserv clipping function for any table with geom, supporting scope + admin filters.';
COMMENT ON FUNCTION gha.admin_whca(integer, integer, integer, integer, text, text, text)
IS 'WHCA admin boundary tiles clipped by optional country/region/district filters.';
""",
            reverse_sql="""
DROP FUNCTION IF EXISTS gha.admin_whca(integer, integer, integer, integer, text, text, text);
DROP FUNCTION IF EXISTS gha.clip_to_scope(integer, integer, integer, text, text, text, text, text, text);
DROP FUNCTION IF EXISTS gha.resolve_scope_extent_geom(text, text, text, text, text);

CREATE FUNCTION gha.admin_whca(
    z integer,
    x integer,
    y integer,
    admin_level integer DEFAULT 0
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
    whca_countries text[] := ARRAY['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    IF admin_level = 0 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id AS gid,
                gid_0,
                country,
                shape_area,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin0
            WHERE geom && tile_bbox_4326
              AND country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 1 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id AS gid,
                gid_0,
                country,
                gid_1,
                name_1 AS region,
                type_1,
                shape_area,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1
            WHERE geom && tile_bbox_4326
              AND country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 2 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id AS gid,
                gid_0,
                country,
                gid_1,
                name_1 AS region,
                gid_2,
                name_2 AS district,
                type_2,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin2
            WHERE geom && tile_bbox_4326
              AND country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;
""",
        ),
    ]
