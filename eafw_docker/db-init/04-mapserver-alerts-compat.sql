-- MapServer alerts compatibility objects
--
-- The mapfiles reference alerts.get_daily_hmc_alerts(), alerts.get_flood_hazard(),
-- and alerts.get_wrf_streamflow(). In this stack the underlying data currently
-- lives in gha.* and wrf.* schemas, so we provide compatibility functions here.

CREATE SCHEMA IF NOT EXISTS alerts;

-- Optional backing table for streamflow ingests.
CREATE TABLE IF NOT EXISTS alerts.wrf_streamflow (
    id SERIAL PRIMARY KEY,
    grid_id INTEGER NOT NULL,
    flow_date DATE NOT NULL,
    flow_level INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_alerts_wrf_streamflow_grid_date UNIQUE (grid_id, flow_date)
);

CREATE INDEX IF NOT EXISTS idx_alerts_wrf_streamflow_date
    ON alerts.wrf_streamflow (flow_date);

CREATE INDEX IF NOT EXISTS idx_alerts_wrf_streamflow_grid
    ON alerts.wrf_streamflow (grid_id);

CREATE INDEX IF NOT EXISTS idx_alerts_wrf_streamflow_level
    ON alerts.wrf_streamflow (flow_level);

CREATE OR REPLACE FUNCTION alerts.get_daily_hmc_alerts(
    date_string TEXT
)
RETURNS TABLE(id INTEGER, alert_level INTEGER, geom GEOMETRY)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        g.id,
        a.alert_level,
        g.cell::geometry AS geom
    FROM wrf.grid_01dd g
    JOIN gha.daily_hmc_alerts a
        ON a.grid_id = g.id
    WHERE a.alert_date = date_string::DATE
      AND a.alert_level > 0;
$$;

CREATE OR REPLACE FUNCTION alerts.get_flood_hazard(
    date_string TEXT,
    country_name TEXT DEFAULT NULL
)
RETURNS TABLE(id INTEGER, hazard_level INTEGER, geom GEOMETRY)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        g.id,
        h.hazard_level,
        g.cell::geometry AS geom
    FROM wrf.grid_01dd g
    JOIN gha.flood_hazard h
        ON h.grid_id = g.id
    WHERE h.hazard_date = date_string::DATE
      AND h.hazard_level > 0
      AND (
          NULLIF(BTRIM(country_name), '') IS NULL
          OR EXISTS (
              SELECT 1
              FROM gha.admin0 a0
              WHERE a0.country = country_name
                AND a0.geom && g.cell
                AND ST_Within(g.cell, a0.geom)
          )
      );
$$;

CREATE OR REPLACE FUNCTION alerts.get_wrf_streamflow(
    date_string TEXT,
    country_name TEXT DEFAULT NULL
)
RETURNS TABLE(id INTEGER, flow_level INTEGER, geom GEOMETRY)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        g.id,
        s.flow_level,
        g.cell::geometry AS geom
    FROM wrf.grid_01dd g
    JOIN alerts.wrf_streamflow s
        ON s.grid_id = g.id
    WHERE s.flow_date = date_string::DATE
      AND s.flow_level > 0
      AND (
          NULLIF(BTRIM(country_name), '') IS NULL
          OR EXISTS (
              SELECT 1
              FROM gha.admin0 a0
              WHERE a0.country = country_name
                AND a0.geom && g.cell
                AND ST_Within(g.cell, a0.geom)
          )
      );
$$;
