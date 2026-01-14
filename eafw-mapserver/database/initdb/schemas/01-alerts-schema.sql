-- EAFW Alerts Schema
-- Create schema for storing FloodWatch alert data

CREATE SCHEMA IF NOT EXISTS alerts;
GRANT USAGE ON SCHEMA alerts TO mapuser;
GRANT USAGE ON SCHEMA alerts TO reader;
