-- Function to Get Daily HMC Alerts by Date
-- Returns grid cells with alert levels for MapServer rendering
-- Borrowed from mukau methodology but simplified for FloodWatch

DROP FUNCTION IF EXISTS alerts.get_daily_hmc_alerts(text);
CREATE OR REPLACE FUNCTION alerts.get_daily_hmc_alerts(
    date_string text  -- Format: YYYY-MM-DD
)
RETURNS TABLE(id integer, alert_level integer, geom geometry)
LANGUAGE 'plpgsql'
COST 100
STABLE PARALLEL SAFE
AS $BODY$
DECLARE
    query_date DATE;
BEGIN
    query_date := date_string::DATE;

    RETURN QUERY
    SELECT
        g.id,
        a.alert_level,
        g.cell::geometry AS geom
    FROM
        grids.grid_01dd g
    INNER JOIN
        alerts.daily_hmc_alerts a ON g.id = a.grid_id
    WHERE
        a.alert_date = query_date
        AND a.alert_level > 0;  -- Only return cells with alerts
END;
$BODY$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION alerts.get_daily_hmc_alerts(text) TO mapuser;
GRANT EXECUTE ON FUNCTION alerts.get_daily_hmc_alerts(text) TO reader;
