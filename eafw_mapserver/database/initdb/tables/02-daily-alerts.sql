-- Daily HMC Alert Data Table
-- Stores FloodProofs HMC hydrological alert levels per grid cell

DROP TABLE IF EXISTS alerts.daily_hmc_alerts CASCADE;
CREATE TABLE alerts.daily_hmc_alerts (
    id SERIAL PRIMARY KEY,
    grid_id INTEGER NOT NULL REFERENCES grids.grid_01dd(id),
    alert_date DATE NOT NULL,
    alert_level INTEGER NOT NULL,  -- 0=None, 1=Watch, 2=Advisory, 3=Warning, 4=Emergency
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(grid_id, alert_date)
);

-- Indexes for fast querying
CREATE INDEX idx_daily_alerts_date ON alerts.daily_hmc_alerts(alert_date);
CREATE INDEX idx_daily_alerts_grid ON alerts.daily_hmc_alerts(grid_id);
CREATE INDEX idx_daily_alerts_level ON alerts.daily_hmc_alerts(alert_level);

-- Grant permissions
GRANT SELECT ON alerts.daily_hmc_alerts TO mapuser;
GRANT SELECT ON alerts.daily_hmc_alerts TO reader;
GRANT INSERT, UPDATE, DELETE ON alerts.daily_hmc_alerts TO gis;
GRANT USAGE, SELECT ON SEQUENCE alerts.daily_hmc_alerts_id_seq TO gis;
