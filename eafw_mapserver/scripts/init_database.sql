-- EAFW MapServer Database Initialization
-- Run this against the CMS database to create grid and alert schemas

-- Create schemas
CREATE SCHEMA IF NOT EXISTS alerts;
CREATE SCHEMA IF NOT EXISTS grids;

-- Create fishnet function
CREATE OR REPLACE FUNCTION public.ST_CreateFishnet(
    nrow integer,
    ncol integer,
    xsize numeric(19,9),
    ysize numeric(19,9),
    x0 numeric(19,9) DEFAULT 0,
    y0 numeric(19,9) DEFAULT 0,
    OUT yrow integer,
    OUT xcol integer,
    OUT cell geometry
)
RETURNS SETOF record AS $$
SELECT i + 1 AS row, j + 1 AS col, ST_Translate(cell, j * $3 + $5, i * $4 + $6) AS geom
FROM generate_series(0, $1 - 1) AS i, generate_series(0, $2 - 1) AS j, (
    SELECT ST_PolygonFromText('POLYGON((0 0, 0 '||$4||', '||$3||' '||$4||', '||$3||' 0,0 0))', 4326) AS cell
) AS foo;
$$ LANGUAGE sql IMMUTABLE STRICT;

-- Create 0.1 degree grid table
DROP TABLE IF EXISTS grids.grid_01dd CASCADE;
CREATE TABLE grids.grid_01dd (
    id SERIAL PRIMARY KEY,
    xcol INTEGER NOT NULL,
    yrow INTEGER NOT NULL,
    cell GEOMETRY(Polygon, 4326) NOT NULL
);

-- Create grid covering EAFW region (lon 21-52, lat -12 to 23)
INSERT INTO grids.grid_01dd (xcol, yrow, cell)
SELECT xcol, yrow, cell
FROM public.ST_CreateFishnet(
    350,      -- rows (latitude range)
    310,      -- cols (longitude range)
    0.1,      -- cell width (degrees)
    0.1,      -- cell height (degrees)
    21.0,     -- x origin (min longitude)
    -12.0     -- y origin (min latitude)
);

-- Create indexes
CREATE INDEX idx_grid_01dd_cell ON grids.grid_01dd USING GIST(cell);
CREATE INDEX idx_grid_01dd_xcol_yrow ON grids.grid_01dd(xcol, yrow);

-- Create daily alerts table
DROP TABLE IF EXISTS alerts.daily_hmc_alerts CASCADE;
CREATE TABLE alerts.daily_hmc_alerts (
    id SERIAL PRIMARY KEY,
    grid_id INTEGER NOT NULL REFERENCES grids.grid_01dd(id),
    alert_date DATE NOT NULL,
    alert_level INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(grid_id, alert_date)
);

CREATE INDEX idx_daily_alerts_date ON alerts.daily_hmc_alerts(alert_date);
CREATE INDEX idx_daily_alerts_grid ON alerts.daily_hmc_alerts(grid_id);
CREATE INDEX idx_daily_alerts_level ON alerts.daily_hmc_alerts(alert_level);

-- Create function to get daily alerts by date
CREATE OR REPLACE FUNCTION alerts.get_daily_hmc_alerts(
    date_string text
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
        AND a.alert_level > 0;
END;
$BODY$;

-- Done
SELECT 'EAFW MapServer database initialized successfully' AS status;
