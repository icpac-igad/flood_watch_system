"""
Add project/admin clipping support to WRF rainfall pg_tileserv functions.

Updates get_total_rainfall_tiles, get_extreme_rainfall_tiles, and
get_daily_rainfall_tiles to accept optional country_name and
project_countries parameters. When supplied, grid cells are filtered
to intersect with the resolved admin/project extent geometry.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0075_merge_0072_seed_cap_settings_0074_mapcategory_fa_icon_class"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
-- =============================================================================
-- wrf.get_total_rainfall_tiles  (with optional clipping)
-- =============================================================================
DROP FUNCTION IF EXISTS wrf.get_total_rainfall_tiles(text);
DROP FUNCTION IF EXISTS wrf.get_total_rainfall_tiles(text, text, text);

CREATE OR REPLACE FUNCTION wrf.get_total_rainfall_tiles(
    p_reference_date  text,
    country_name      text DEFAULT NULL,
    project_countries text DEFAULT NULL
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    clip_geom geometry;
BEGIN
    -- Resolve clipping extent when filters are provided
    IF (country_name IS NOT NULL AND trim(country_name) <> '')
       OR (project_countries IS NOT NULL AND trim(project_countries) <> '') THEN
        clip_geom := gha.resolve_scope_extent_geom(
            CASE
                WHEN project_countries IS NOT NULL AND trim(project_countries) <> '' THEN 'project'
                ELSE 'all'
            END,
            project_countries,
            country_name,
            NULL,
            NULL
        );
    END IF;

    RETURN QUERY
    WITH selected_run AS (
        SELECT max(r.forecast_date) AS forecast_date
        FROM wrf.daily_rainfall r
        WHERE p_reference_date::date BETWEEN r.forecast_date AND (r.forecast_date + INTERVAL '7 days')
    ),
    weekly_totals AS (
        SELECT
            r.grid_id,
            SUM(r.rainfall_mm)::numeric AS rainfall_mm
        FROM wrf.daily_rainfall r
        JOIN selected_run sr ON r.forecast_date = sr.forecast_date
        WHERE r.valid_date BETWEEN r.forecast_date AND (r.forecast_date + INTERVAL '7 days')
        GROUP BY r.grid_id
    )
    SELECT
        g.id,
        w.rainfall_mm,
        g.cell
    FROM wrf.grid_01dd g
    JOIN weekly_totals w ON w.grid_id = g.id
    WHERE w.rainfall_mm > 0
      AND (clip_geom IS NULL OR ST_Intersects(g.cell, clip_geom));
END;
$function$;

COMMENT ON FUNCTION wrf.get_total_rainfall_tiles(text, text, text)
IS 'Weekly total rainfall tiles with optional country/project clipping via pg_tileserv.';

-- =============================================================================
-- wrf.get_extreme_rainfall_tiles  (with optional clipping)
-- =============================================================================
DROP FUNCTION IF EXISTS wrf.get_extreme_rainfall_tiles(text, text);
DROP FUNCTION IF EXISTS wrf.get_extreme_rainfall_tiles(text, text, text, text);

CREATE OR REPLACE FUNCTION wrf.get_extreme_rainfall_tiles(
    p_forecast_date   text,
    p_percentile      text DEFAULT 'f95',
    country_name      text DEFAULT NULL,
    project_countries text DEFAULT NULL
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    clip_geom geometry;
BEGIN
    -- Resolve clipping extent when filters are provided
    IF (country_name IS NOT NULL AND trim(country_name) <> '')
       OR (project_countries IS NOT NULL AND trim(project_countries) <> '') THEN
        clip_geom := gha.resolve_scope_extent_geom(
            CASE
                WHEN project_countries IS NOT NULL AND trim(project_countries) <> '' THEN 'project'
                ELSE 'all'
            END,
            project_countries,
            country_name,
            NULL,
            NULL
        );
    END IF;

    IF p_percentile = 'f90' THEN
        RETURN QUERY
            SELECT g.id, r.f90_mm, g.cell
            FROM wrf.grid_01dd g
            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
            WHERE r.forecast_date = p_forecast_date::date
              AND r.f90_mm > 0
              AND (clip_geom IS NULL OR ST_Intersects(g.cell, clip_geom));
    ELSIF p_percentile = 'f99' THEN
        RETURN QUERY
            SELECT g.id, r.f99_mm, g.cell
            FROM wrf.grid_01dd g
            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
            WHERE r.forecast_date = p_forecast_date::date
              AND r.f99_mm > 0
              AND (clip_geom IS NULL OR ST_Intersects(g.cell, clip_geom));
    ELSE
        RETURN QUERY
            SELECT g.id, r.f95_mm, g.cell
            FROM wrf.grid_01dd g
            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
            WHERE r.forecast_date = p_forecast_date::date
              AND r.f95_mm > 0
              AND (clip_geom IS NULL OR ST_Intersects(g.cell, clip_geom));
    END IF;
END;
$function$;

COMMENT ON FUNCTION wrf.get_extreme_rainfall_tiles(text, text, text, text)
IS 'Extreme rainfall percentile tiles with optional country/project clipping via pg_tileserv.';

-- =============================================================================
-- wrf.get_daily_rainfall_tiles  (with optional clipping)
-- =============================================================================
DROP FUNCTION IF EXISTS wrf.get_daily_rainfall_tiles(text);
DROP FUNCTION IF EXISTS wrf.get_daily_rainfall_tiles(text, text, text);

CREATE OR REPLACE FUNCTION wrf.get_daily_rainfall_tiles(
    p_valid_date      text,
    country_name      text DEFAULT NULL,
    project_countries text DEFAULT NULL
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    clip_geom geometry;
BEGIN
    -- Resolve clipping extent when filters are provided
    IF (country_name IS NOT NULL AND trim(country_name) <> '')
       OR (project_countries IS NOT NULL AND trim(project_countries) <> '') THEN
        clip_geom := gha.resolve_scope_extent_geom(
            CASE
                WHEN project_countries IS NOT NULL AND trim(project_countries) <> '' THEN 'project'
                ELSE 'all'
            END,
            project_countries,
            country_name,
            NULL,
            NULL
        );
    END IF;

    RETURN QUERY
    SELECT g.id, r.rainfall_mm, g.cell
    FROM wrf.grid_01dd g
    JOIN wrf.daily_rainfall r ON g.id = r.grid_id
    WHERE r.valid_date = p_valid_date::date
      AND r.rainfall_mm > 0
      AND (clip_geom IS NULL OR ST_Intersects(g.cell, clip_geom));
END;
$function$;

COMMENT ON FUNCTION wrf.get_daily_rainfall_tiles(text, text, text)
IS 'Daily rainfall tiles with optional country/project clipping via pg_tileserv.';

-- Grant access for pg_tileserv
GRANT EXECUTE ON FUNCTION wrf.get_total_rainfall_tiles(text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION wrf.get_extreme_rainfall_tiles(text, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION wrf.get_daily_rainfall_tiles(text, text, text) TO PUBLIC;
""",
            reverse_sql="""
-- Restore original functions without clipping
DROP FUNCTION IF EXISTS wrf.get_total_rainfall_tiles(text, text, text);
DROP FUNCTION IF EXISTS wrf.get_extreme_rainfall_tiles(text, text, text, text);
DROP FUNCTION IF EXISTS wrf.get_daily_rainfall_tiles(text, text, text);

CREATE OR REPLACE FUNCTION wrf.get_total_rainfall_tiles(
    p_reference_date text
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE sql
STABLE
AS $function$
    WITH selected_run AS (
        SELECT max(r.forecast_date) AS forecast_date
        FROM wrf.daily_rainfall r
        WHERE p_reference_date::date BETWEEN r.forecast_date AND (r.forecast_date + INTERVAL '7 days')
    ),
    weekly_totals AS (
        SELECT
            r.grid_id AS id,
            SUM(r.rainfall_mm)::numeric AS rainfall_mm
        FROM wrf.daily_rainfall r
        JOIN selected_run sr ON r.forecast_date = sr.forecast_date
        WHERE r.valid_date BETWEEN r.forecast_date AND (r.forecast_date + INTERVAL '7 days')
        GROUP BY r.grid_id
    )
    SELECT
        g.id,
        w.rainfall_mm,
        g.cell
    FROM wrf.grid_01dd g
    JOIN weekly_totals w ON w.id = g.id
    WHERE w.rainfall_mm > 0;
$function$;

CREATE OR REPLACE FUNCTION wrf.get_extreme_rainfall_tiles(
    p_forecast_date text,
    p_percentile text DEFAULT 'f95'
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE plpgsql
STABLE
AS $function$
BEGIN
    IF p_percentile = 'f90' THEN
        RETURN QUERY
            SELECT g.id, r.f90_mm, g.cell
            FROM wrf.grid_01dd g
            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
            WHERE r.forecast_date = p_forecast_date::date
              AND r.f90_mm > 0;
    ELSIF p_percentile = 'f99' THEN
        RETURN QUERY
            SELECT g.id, r.f99_mm, g.cell
            FROM wrf.grid_01dd g
            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
            WHERE r.forecast_date = p_forecast_date::date
              AND r.f99_mm > 0;
    ELSE
        RETURN QUERY
            SELECT g.id, r.f95_mm, g.cell
            FROM wrf.grid_01dd g
            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
            WHERE r.forecast_date = p_forecast_date::date
              AND r.f95_mm > 0;
    END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION wrf.get_daily_rainfall_tiles(
    p_valid_date text
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE sql
STABLE
AS $function$
    SELECT g.id, r.rainfall_mm, g.cell
    FROM wrf.grid_01dd g
    JOIN wrf.daily_rainfall r ON g.id = r.grid_id
    WHERE r.valid_date = p_valid_date::date
      AND r.rainfall_mm > 0;
$function$;
""",
        ),
    ]
