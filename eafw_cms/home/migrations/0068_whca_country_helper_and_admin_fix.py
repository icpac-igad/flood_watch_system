from django.db import migrations


FORWARD_SQL = """
-- Single source of truth for WHCA member countries.
-- Referenced by admin_whca, resolve_scope_extent_geom, resolve_whca_extent_geom.
CREATE OR REPLACE FUNCTION gha.get_whca_countries()
RETURNS text[]
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT ARRAY['Sudan', 'South Sudan', 'Uganda', 'Ethiopia', 'Rwanda'];
$function$;

GRANT EXECUTE ON FUNCTION gha.get_whca_countries() TO PUBLIC;
COMMENT ON FUNCTION gha.get_whca_countries()
IS 'Returns the canonical list of WHCA member countries. Single source of truth.';


-- Rewrite admin_whca to use get_whca_countries() for explicit country
-- membership AND resolve_scope_extent_geom for spatial clipping when
-- admin sub-filters (country/region/district) are applied.
DROP FUNCTION IF EXISTS gha.admin_whca(integer, integer, integer, integer, text, text, text);

CREATE OR REPLACE FUNCTION gha.admin_whca(
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
    scope_geom geometry;
    effective_geom geometry;
    whca_countries text[] := gha.get_whca_countries();
    has_admin_filter boolean := (
        (country_name IS NOT NULL AND trim(country_name) <> '')
        OR (region_name IS NOT NULL AND trim(region_name) <> '')
        OR (district_name IS NOT NULL AND trim(district_name) <> '')
    );
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    -- Use scope resolution for spatial clipping (respects admin sub-filters)
    scope_geom := gha.resolve_scope_extent_geom(
        'whca',
        NULL,
        country_name,
        region_name,
        district_name
    );

    IF scope_geom IS NULL OR ST_IsEmpty(scope_geom) THEN
        RETURN ''::bytea;
    END IF;

    effective_geom := gha.clip_geom_to_admin_extent(tile_bbox_4326, scope_geom);

    IF effective_geom IS NULL OR ST_IsEmpty(effective_geom) THEN
        RETURN ''::bytea;
    END IF;

    IF admin_level = 1 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.gid_1,
                a.name_1 AS region,
                a.type_1,
                a.shape_area,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (NOT has_admin_filter OR (
                  (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
                  AND (region_name IS NULL OR trim(region_name) = '' OR a.name_1 = region_name)
              ))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 2 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.gid_1,
                a.name_1 AS region,
                a.gid_2,
                a.name_2 AS district,
                a.type_2,
                a.shape_area,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin2 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (NOT has_admin_filter OR (
                  (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
                  AND (region_name IS NULL OR trim(region_name) = '' OR a.name_1 = region_name)
                  AND (district_name IS NULL OR trim(district_name) = '' OR a.name_2 = district_name)
              ))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSE
        -- admin0: explicit country membership + optional clipping for sub-filters
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.shape_area,
                ST_AsMVTGeom(
                    ST_Transform(
                        CASE
                            WHEN has_admin_filter THEN gha.clip_geom_to_admin_extent(a.geom, effective_geom)
                            ELSE a.geom
                        END,
                        3857
                    ),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin0 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.admin_whca(integer, integer, integer, integer, text, text, text) TO PUBLIC;
COMMENT ON FUNCTION gha.admin_whca(integer, integer, integer, integer, text, text, text)
IS 'WHCA admin boundary tiles filtered by country membership (via get_whca_countries) with optional admin sub-filters.';


-- Update resolve_whca_extent_geom to use get_whca_countries()
CREATE OR REPLACE FUNCTION gha.resolve_whca_extent_geom()
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    scope_geom geometry;
BEGIN
    IF to_regclass('gha.nile_basin_mask') IS NOT NULL THEN
        EXECUTE 'SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) FROM gha.nile_basin_mask'
        INTO scope_geom;

        IF scope_geom IS NOT NULL AND NOT ST_IsEmpty(scope_geom) THEN
            RETURN scope_geom;
        END IF;
    END IF;

    IF to_regclass('gha.hydrobasins_lev06') IS NOT NULL THEN
        EXECUTE $$
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom))))
            FROM gha.hydrobasins_lev06
            WHERE main_bas IN (1020034170, 1060000010)
        $$ INTO scope_geom;

        IF scope_geom IS NOT NULL AND NOT ST_IsEmpty(scope_geom) THEN
            RETURN scope_geom;
        END IF;
    ELSIF to_regclass('gha.hydrobasins_level06') IS NOT NULL THEN
        EXECUTE $$
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom))))
            FROM gha.hydrobasins_level06
            WHERE main_bas IN (1020034170, 1060000010)
        $$ INTO scope_geom;

        IF scope_geom IS NOT NULL AND NOT ST_IsEmpty(scope_geom) THEN
            RETURN scope_geom;
        END IF;
    END IF;

    -- Last resort: WHCA country union using canonical list
    SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO scope_geom
    FROM gha.admin0
    WHERE country = ANY(gha.get_whca_countries());

    RETURN scope_geom;
END;
$function$;


-- Update resolve_scope_extent_geom to use get_whca_countries()
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
    whca_countries text[] := gha.get_whca_countries();
BEGIN
    admin_geom := gha.resolve_admin_extent_geom(country_name, region_name, district_name);

    IF normalized_scope = 'all' AND (project_countries IS NULL OR trim(project_countries) = '') THEN
        RETURN admin_geom;
    END IF;

    IF normalized_scope = 'whca' THEN
        scope_geom := gha.resolve_whca_extent_geom();
    ELSIF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        countries_arr := regexp_split_to_array(project_countries, '\\s*,\\s*');

        SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO scope_geom
        FROM gha.admin0
        WHERE country = ANY(countries_arr)
          AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
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
       AND NOT EXISTS (
           SELECT 1
           FROM unnest(whca_countries) AS whca(country)
           WHERE lower(trim(whca.country)) = lower(trim(country_name))
       ) THEN
        RETURN NULL;
    END IF;

    IF project_countries IS NOT NULL
       AND trim(project_countries) <> ''
       AND country_name IS NOT NULL
       AND trim(country_name) <> ''
       AND NOT EXISTS (
           SELECT 1
           FROM unnest(countries_arr) AS project(country)
           WHERE lower(trim(project.country)) = lower(trim(country_name))
       ) THEN
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
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0067_rename_whca_site_title_hydromet"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
