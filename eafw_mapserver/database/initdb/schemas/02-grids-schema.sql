-- EAFW Grids Schema
-- Create schema for storing grid geometries

CREATE SCHEMA IF NOT EXISTS grids;
GRANT USAGE ON SCHEMA grids TO mapuser;
GRANT USAGE ON SCHEMA grids TO reader;
