from django.db import migrations


FORWARD_SQL = """
-- Remove Eritrea geometries from admin boundary tables
DELETE FROM gha.admin2
WHERE LOWER(TRIM(COALESCE(country, ''))) = 'eritrea'
   OR UPPER(TRIM(COALESCE(gid_0, ''))) = 'ERI';

DELETE FROM gha.admin1
WHERE LOWER(TRIM(COALESCE(country, ''))) = 'eritrea'
   OR UPPER(TRIM(COALESCE(gid_0, ''))) = 'ERI';

DELETE FROM gha.admin0
WHERE LOWER(TRIM(COALESCE(country, ''))) = 'eritrea'
   OR UPPER(TRIM(COALESCE(gid_0, ''))) = 'ERI';

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
    FROM gha.admin0
    WHERE country IS NOT NULL
      AND TRIM(country) <> ''
      AND LOWER(TRIM(country)) <> 'eritrea';

    INSERT INTO gha.admin_extent_cache(id, geom, updated_at)
    VALUES (TRUE, merged_geom, now())
    ON CONFLICT (id) DO UPDATE
    SET geom = EXCLUDED.geom,
        updated_at = EXCLUDED.updated_at;
END;
$function$;

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
    has_filters boolean := (
        (country_name IS NOT NULL AND country_name <> '')
        OR (region_name IS NOT NULL AND region_name <> '')
        OR (district_name IS NOT NULL AND district_name <> '')
    );
BEGIN
    IF NOT has_filters THEN
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

    IF LOWER(TRIM(COALESCE(country_name, ''))) = 'eritrea' THEN
        RETURN NULL;
    END IF;

    IF district_name IS NOT NULL AND district_name <> '' THEN
        SELECT ST_UnaryUnion(ST_Collect(geom)) INTO clip_geom
        FROM gha.admin2
        WHERE name_2 = district_name
          AND (region_name IS NULL OR region_name = '' OR name_1 = region_name)
          AND (country_name IS NULL OR country_name = '' OR country = country_name)
          AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
    ELSIF region_name IS NOT NULL AND region_name <> '' THEN
        SELECT ST_UnaryUnion(ST_Collect(geom)) INTO clip_geom
        FROM gha.admin1
        WHERE name_1 = region_name
          AND (country_name IS NULL OR country_name = '' OR country = country_name)
          AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
    ELSIF country_name IS NOT NULL AND country_name <> '' THEN
        SELECT ST_UnaryUnion(ST_Collect(geom)) INTO clip_geom
        FROM gha.admin0
        WHERE country = country_name
          AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
    END IF;

    IF clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
        RETURN NULL;
    END IF;

    RETURN clip_geom;
END;
$function$;

CREATE OR REPLACE FUNCTION gha.get_admin_clip_geom(
    admin_level text DEFAULT 'all',
    admin_name text DEFAULT NULL,
    country_filter text DEFAULT NULL
)
RETURNS geometry
LANGUAGE plpgsql
STABLE PARALLEL SAFE
AS $fn$
DECLARE
    clip_geom geometry;
    norm_level text := lower(COALESCE(NULLIF(trim(admin_level), ''), 'all'));
BEGIN
    IF norm_level = 'all' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin_extent_cache WHERE id = TRUE LIMIT 1;
        IF clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
            PERFORM gha.refresh_admin_extent_cache();
            SELECT geom INTO clip_geom FROM gha.admin_extent_cache WHERE id = TRUE LIMIT 1;
        END IF;
        RETURN clip_geom;
    END IF;

    IF norm_level = 'admin0' OR norm_level = 'country' THEN
        IF admin_name IS NOT NULL AND trim(admin_name) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin0
            WHERE country = admin_name
              AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        ELSE
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin0
            WHERE LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        END IF;
        RETURN clip_geom;
    END IF;

    IF norm_level = 'admin1' OR norm_level = 'region' THEN
        IF admin_name IS NOT NULL AND trim(admin_name) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin1
            WHERE name_1 = admin_name
              AND (country_filter IS NULL OR trim(country_filter) = '' OR country = country_filter)
              AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        ELSIF country_filter IS NOT NULL AND trim(country_filter) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin1
            WHERE country = country_filter
              AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        ELSE
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin1
            WHERE LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        END IF;
        RETURN clip_geom;
    END IF;

    IF norm_level = 'admin2' OR norm_level = 'district' THEN
        IF admin_name IS NOT NULL AND trim(admin_name) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin2
            WHERE name_2 = admin_name
              AND (country_filter IS NULL OR trim(country_filter) = '' OR country = country_filter)
              AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        ELSIF country_filter IS NOT NULL AND trim(country_filter) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin2
            WHERE country = country_filter
              AND LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        ELSE
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin2
            WHERE LOWER(TRIM(COALESCE(country, ''))) <> 'eritrea';
        END IF;
        RETURN clip_geom;
    END IF;

    SELECT geom INTO clip_geom FROM gha.admin_extent_cache WHERE id = TRUE LIMIT 1;
    RETURN clip_geom;
END;
$fn$;

CREATE OR REPLACE FUNCTION gha.list_admin_names(
    admin_level text DEFAULT 'admin0',
    country_filter text DEFAULT NULL
)
RETURNS TABLE(name text, country text)
LANGUAGE plpgsql
STABLE PARALLEL SAFE
AS $fn$
DECLARE
    norm_level text := lower(COALESCE(NULLIF(trim(admin_level), ''), 'admin0'));
BEGIN
    IF norm_level = 'admin0' OR norm_level = 'country' THEN
        RETURN QUERY
            SELECT a.country::text, a.country::text
            FROM gha.admin0 a
            WHERE LOWER(TRIM(COALESCE(a.country, ''))) <> 'eritrea'
            ORDER BY a.country;
    ELSIF norm_level = 'admin1' OR norm_level = 'region' THEN
        RETURN QUERY
            SELECT a.name_1::text, a.country::text
            FROM gha.admin1 a
            WHERE (country_filter IS NULL OR trim(country_filter) = '' OR a.country = country_filter)
              AND LOWER(TRIM(COALESCE(a.country, ''))) <> 'eritrea'
            ORDER BY a.country, a.name_1;
    ELSIF norm_level = 'admin2' OR norm_level = 'district' THEN
        RETURN QUERY
            SELECT a.name_2::text, a.country::text
            FROM gha.admin2 a
            WHERE (country_filter IS NULL OR trim(country_filter) = '' OR a.country = country_filter)
              AND LOWER(TRIM(COALESCE(a.country, ''))) <> 'eritrea'
            ORDER BY a.country, a.name_2;
    END IF;
END;
$fn$;

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

SELECT gha.refresh_admin_extent_cache();

GRANT EXECUTE ON FUNCTION gha.refresh_admin_extent_cache() TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.resolve_admin_extent_geom(text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.get_admin_clip_geom(text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.list_admin_names(text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.resolve_scope_extent_geom(text, text, text, text, text) TO PUBLIC;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0056_update_partner_copy_defaults"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
