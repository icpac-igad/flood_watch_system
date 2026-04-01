-- Compatibility wrappers for scope-aware WRF mapserver layers.
--
-- The clean stack currently ships mapfiles that call scope/project-aware WRF
-- SQL helpers, while the database only has the older narrow signatures:
--   wrf.get_total_rainfall_tiles(text)
--   wrf.get_extreme_rainfall_tiles(text, text)
--
-- Add wrapper overloads so homepage/minimap rainfall tiles render without
-- rewriting the existing mapfiles. Scope and project filters are still
-- enforced by the admin extent mask in MapServer.

CREATE OR REPLACE FUNCTION wrf.get_total_rainfall_tiles(
    p_reference_date text,
    p_unused text,
    p_project_countries text,
    p_scope text
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE sql
STABLE
AS $function$
    SELECT t.id, t.rainfall_mm, t.geom
    FROM wrf.get_total_rainfall_tiles(p_reference_date) AS t;
$function$;


CREATE OR REPLACE FUNCTION wrf.get_extreme_rainfall_tiles(
    p_forecast_date text,
    p_percentile text,
    p_scope text,
    p_project_countries text
)
RETURNS TABLE(id integer, rainfall_mm numeric, geom geometry)
LANGUAGE sql
STABLE
AS $function$
    SELECT t.id, t.rainfall_mm, t.geom
    FROM wrf.get_extreme_rainfall_tiles(p_forecast_date, p_percentile) AS t;
$function$;


GRANT EXECUTE ON FUNCTION wrf.get_total_rainfall_tiles(text, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION wrf.get_extreme_rainfall_tiles(text, text, text, text) TO PUBLIC;
