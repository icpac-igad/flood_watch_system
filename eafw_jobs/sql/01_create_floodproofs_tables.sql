-- FloodProofs Data Tables for eahw_mapserver database

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS floodproofs;

-- Merged Deterministic GeoJSON Table
CREATE TABLE IF NOT EXISTS floodproofs.merged_deterministic_geojson (
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_merged_deterministic_data_date
    ON floodproofs.merged_deterministic_geojson(data_date DESC);
CREATE INDEX IF NOT EXISTS idx_merged_deterministic_created_at
    ON floodproofs.merged_deterministic_geojson(created_at DESC);

-- Ensemble Forecast GeoJSON Table
CREATE TABLE IF NOT EXISTS floodproofs.ensemble_forecast_geojson (
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ensemble_forecast_data_date
    ON floodproofs.ensemble_forecast_geojson(data_date DESC);
CREATE INDEX IF NOT EXISTS idx_ensemble_forecast_created_at
    ON floodproofs.ensemble_forecast_geojson(created_at DESC);

-- Grant permissions to ingest_user
GRANT ALL PRIVILEGES ON SCHEMA floodproofs TO ingest_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA floodproofs TO ingest_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA floodproofs TO ingest_user;

-- Comments
COMMENT ON TABLE floodproofs.merged_deterministic_geojson IS 'FloodProofs merged deterministic forecast data (GFS+ICON models)';
COMMENT ON TABLE floodproofs.ensemble_forecast_geojson IS 'FloodProofs multi-model ensemble forecast data';
