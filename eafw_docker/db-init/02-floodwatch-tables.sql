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

DO $$ BEGIN RAISE NOTICE 'FloodWatch forecast tables created in gha schema'; END $$;
