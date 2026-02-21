"""Create reusable PostGIS functions for admin boundary clipping.

Functions:
- gha.get_admin_clip_geom(admin_level, admin_name, country_filter)
  Returns geometry for clipping/masking at any admin level.
- gha.get_admin_clip_geojson(admin_level, admin_name, country_filter)
  Returns GeoJSON text of the clip geometry.
- gha.list_admin_names(admin_level, country_filter)
  Lists available admin names at a given level.
"""

from django.db import migrations


FORWARD_SQL = """
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
    -- Level: all — return merged GHoA extent (cached)
    IF norm_level = 'all' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin_extent_cache WHERE id = TRUE LIMIT 1;
        IF clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
            PERFORM gha.refresh_admin_extent_cache();
            SELECT geom INTO clip_geom FROM gha.admin_extent_cache WHERE id = TRUE LIMIT 1;
        END IF;
        RETURN clip_geom;
    END IF;

    -- Level: admin0 / country
    IF norm_level = 'admin0' OR norm_level = 'country' THEN
        IF admin_name IS NOT NULL AND trim(admin_name) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin0 WHERE country = admin_name;
        ELSE
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin0;
        END IF;
        RETURN clip_geom;
    END IF;

    -- Level: admin1 / region
    IF norm_level = 'admin1' OR norm_level = 'region' THEN
        IF admin_name IS NOT NULL AND trim(admin_name) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin1
            WHERE name_1 = admin_name
              AND (country_filter IS NULL OR trim(country_filter) = '' OR country = country_filter);
        ELSIF country_filter IS NOT NULL AND trim(country_filter) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin1 WHERE country = country_filter;
        ELSE
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin1;
        END IF;
        RETURN clip_geom;
    END IF;

    -- Level: admin2 / district
    IF norm_level = 'admin2' OR norm_level = 'district' THEN
        IF admin_name IS NOT NULL AND trim(admin_name) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin2
            WHERE name_2 = admin_name
              AND (country_filter IS NULL OR trim(country_filter) = '' OR country = country_filter);
        ELSIF country_filter IS NOT NULL AND trim(country_filter) <> '' THEN
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin2 WHERE country = country_filter;
        ELSE
            SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO clip_geom
            FROM gha.admin2;
        END IF;
        RETURN clip_geom;
    END IF;

    -- Fallback: return full extent
    SELECT geom INTO clip_geom FROM gha.admin_extent_cache WHERE id = TRUE LIMIT 1;
    RETURN clip_geom;
END;
$fn$;


CREATE OR REPLACE FUNCTION gha.get_admin_clip_geojson(
    admin_level text DEFAULT 'all',
    admin_name text DEFAULT NULL,
    country_filter text DEFAULT NULL
)
RETURNS text
LANGUAGE sql
STABLE PARALLEL SAFE
AS $fn$
    SELECT ST_AsGeoJSON(gha.get_admin_clip_geom(admin_level, admin_name, country_filter), 6);
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
        RETURN QUERY SELECT a.country::text, a.country::text FROM gha.admin0 a ORDER BY a.country;
    ELSIF norm_level = 'admin1' OR norm_level = 'region' THEN
        RETURN QUERY SELECT a.name_1::text, a.country::text FROM gha.admin1 a
            WHERE (country_filter IS NULL OR trim(country_filter) = '' OR a.country = country_filter)
            ORDER BY a.country, a.name_1;
    ELSIF norm_level = 'admin2' OR norm_level = 'district' THEN
        RETURN QUERY SELECT a.name_2::text, a.country::text FROM gha.admin2 a
            WHERE (country_filter IS NULL OR trim(country_filter) = '' OR a.country = country_filter)
            ORDER BY a.country, a.name_2;
    END IF;
END;
$fn$;
"""

REVERSE_SQL = """
DROP FUNCTION IF EXISTS gha.list_admin_names(text, text);
DROP FUNCTION IF EXISTS gha.get_admin_clip_geojson(text, text, text);
DROP FUNCTION IF EXISTS gha.get_admin_clip_geom(text, text, text);
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0053_footer_partners_visibility_toggles"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
