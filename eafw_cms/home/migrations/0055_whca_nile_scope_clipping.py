from django.db import migrations


FORWARD_SQL = """
CREATE OR REPLACE FUNCTION gha.resolve_whca_extent_geom()
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    scope_geom geometry;
BEGIN
    -- 1) Preferred source: explicit WHCA/Nile mask table
    IF to_regclass('gha.nile_basin_mask') IS NOT NULL THEN
        EXECUTE 'SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) FROM gha.nile_basin_mask'
        INTO scope_geom;

        IF scope_geom IS NOT NULL AND NOT ST_IsEmpty(scope_geom) THEN
            RETURN scope_geom;
        END IF;
    END IF;

    -- 2) Fallback source: HydroBASINS (if present)
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

    -- 3) Last resort: WHCA country union
    SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO scope_geom
    FROM gha.admin0
    WHERE country = ANY(ARRAY['Sudan', 'South Sudan', 'Uganda', 'Ethiopia', 'Rwanda']);

    RETURN scope_geom;
END;
$function$;


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
        scope_geom := gha.resolve_whca_extent_geom();
    ELSIF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        countries_arr := regexp_split_to_array(project_countries, '\\s*,\\s*');

        SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO scope_geom
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

GRANT EXECUTE ON FUNCTION gha.resolve_whca_extent_geom() TO PUBLIC;
COMMENT ON FUNCTION gha.resolve_whca_extent_geom()
IS 'Resolves WHCA extent using Nile basin geometry (mask table or HydroBASINS), with country-union fallback.';
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0054_create_admin_clip_functions"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
