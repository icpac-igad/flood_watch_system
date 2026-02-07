-- EAFW FloodWatch - Tables in gha schema
-- Forecast data tables (no alerts)

-- ============================================
-- FLOODPROOFS MERGED DETERMINISTIC GEOJSON
-- Stores merged GFS+ICON forecast data
-- ============================================
CREATE TABLE IF NOT EXISTS gha.merged_deterministic_geojson (
    id SERIAL PRIMARY KEY,
    data_date DATE UNIQUE NOT NULL,
    date_string VARCHAR(8) UNIQUE NOT NULL,
    geojson_data JSONB NOT NULL,
    feature_count INTEGER NOT NULL,
    file_count INTEGER DEFAULT 1,
    file_path VARCHAR(500),
    processed_by VARCHAR(100) DEFAULT 'floodwatch_jobs',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_merged_deterministic_data_date ON gha.merged_deterministic_geojson(data_date DESC);
CREATE INDEX IF NOT EXISTS idx_merged_deterministic_created_at ON gha.merged_deterministic_geojson(created_at DESC);

GRANT SELECT ON gha.merged_deterministic_geojson TO mapuser;
GRANT SELECT ON gha.merged_deterministic_geojson TO reader;
GRANT ALL ON gha.merged_deterministic_geojson TO ingest_user;
GRANT USAGE, SELECT ON SEQUENCE gha.merged_deterministic_geojson_id_seq TO ingest_user;

-- ============================================
-- FLOODPROOFS ENSEMBLE FORECAST GEOJSON
-- Stores multi-model ensemble forecast data
-- ============================================
CREATE TABLE IF NOT EXISTS gha.ensemble_forecast_geojson (
    id SERIAL PRIMARY KEY,
    data_date DATE UNIQUE NOT NULL,
    date_string VARCHAR(8) UNIQUE NOT NULL,
    geojson_data JSONB NOT NULL,
    feature_count INTEGER NOT NULL,
    matched_count INTEGER NOT NULL,
    processed_by VARCHAR(100) DEFAULT 'floodwatch_jobs',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ensemble_forecast_data_date ON gha.ensemble_forecast_geojson(data_date DESC);
CREATE INDEX IF NOT EXISTS idx_ensemble_forecast_created_at ON gha.ensemble_forecast_geojson(created_at DESC);

GRANT SELECT ON gha.ensemble_forecast_geojson TO mapuser;
GRANT SELECT ON gha.ensemble_forecast_geojson TO reader;
GRANT ALL ON gha.ensemble_forecast_geojson TO ingest_user;
GRANT USAGE, SELECT ON SEQUENCE gha.ensemble_forecast_geojson_id_seq TO ingest_user;

-- ============================================
-- MULTIMODAL CONTROL POINTS
-- 3199 river monitoring stations across GHoA
-- Data loaded via 03_multimodal_control_points.sql.gz
-- ============================================
CREATE TABLE IF NOT EXISTS gha.multimodal_control_points (
    point_id INTEGER PRIMARY KEY,
    gridcode INTEGER,
    admin_name TEXT,
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    zone INTEGER,
    is_node BOOLEAN,
    geom geometry(Point,4326),
    whca_selected BOOLEAN,
    hybas_id BIGINT,
    main_bas BIGINT,
    coord_id TEXT,
    country_code VARCHAR(2)
);

CREATE INDEX IF NOT EXISTS idx_multimodal_control_points_geom ON gha.multimodal_control_points USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_control_points_country ON gha.multimodal_control_points (country_code);

GRANT SELECT ON gha.multimodal_control_points TO mapuser;
GRANT SELECT ON gha.multimodal_control_points TO reader;
GRANT ALL ON gha.multimodal_control_points TO ingest_user;

-- ============================================
-- MULTIMODAL FORECASTS
-- Daily ensemble forecasts per control point
-- Populated by jobs scheduler (daily sync)
-- ============================================
CREATE TABLE IF NOT EXISTS gha.multimodal_forecasts (
    id SERIAL PRIMARY KEY,
    point_id INTEGER NOT NULL,
    data_date DATE NOT NULL,
    forecast_date DATE NOT NULL,
    daily_avg DOUBLE PRECISION,
    daily_max DOUBLE PRECISION,
    daily_min DOUBLE PRECISION,
    geosfm DOUBLE PRECISION,
    floodproof DOUBLE PRECISION,
    mike_hydro_rfe DOUBLE PRECISION,
    mike_hydro_chirp DOUBLE PRECISION,
    mike_hydro_imerg DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (point_id, data_date, forecast_date)
);

CREATE INDEX IF NOT EXISTS idx_mm_forecasts_data_date ON gha.multimodal_forecasts (data_date);
CREATE INDEX IF NOT EXISTS idx_mm_forecasts_point_date ON gha.multimodal_forecasts (point_id, data_date);

GRANT SELECT ON gha.multimodal_forecasts TO mapuser;
GRANT SELECT ON gha.multimodal_forecasts TO reader;
GRANT ALL ON gha.multimodal_forecasts TO ingest_user;
GRANT USAGE, SELECT ON SEQUENCE gha.multimodal_forecasts_id_seq TO ingest_user;

DO $$ BEGIN RAISE NOTICE 'FloodWatch tables created: deterministic, ensemble, control_points, forecasts'; END $$;
