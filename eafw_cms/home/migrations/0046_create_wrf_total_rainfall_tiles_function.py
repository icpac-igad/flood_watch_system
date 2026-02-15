from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0045_add_wrf_rainfall_metadata"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
DROP FUNCTION IF EXISTS wrf.get_total_rainfall_tiles(text);

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
            """,
            reverse_sql="""
DROP FUNCTION IF EXISTS wrf.get_total_rainfall_tiles(text);
            """,
        ),
    ]
