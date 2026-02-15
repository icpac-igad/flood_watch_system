# Migration to create MapServer-compatible SQL functions for WRF rainfall tiles.
# These text-parameter overloads allow MapServer's %time% string substitution
# to work directly without explicit casting.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0041_add_unmanaged_report_snapshot_model"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
-- =============================================================================
-- wrf.get_daily_rainfall_tiles(text)
-- MapServer-compatible function for daily rainfall WMS tiles.
-- Accepts text param (MapServer does %time% string substitution).
-- Returns grid cells with rainfall > 0 for the given valid_date.
-- =============================================================================

DROP FUNCTION IF EXISTS wrf.get_daily_rainfall_tiles(text);

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

-- =============================================================================
-- wrf.get_extreme_rainfall_tiles(text, text)
-- MapServer-compatible function for extreme rainfall WMS tiles.
-- Accepts text params for date and percentile (f90/f95/f99).
-- Returns grid cells with rainfall > 0 for the given forecast_date + percentile.
-- =============================================================================

DROP FUNCTION IF EXISTS wrf.get_extreme_rainfall_tiles(text, text);

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
            """,
            reverse_sql="""
DROP FUNCTION IF EXISTS wrf.get_daily_rainfall_tiles(text);
DROP FUNCTION IF EXISTS wrf.get_extreme_rainfall_tiles(text, text);
            """,
        ),
    ]
