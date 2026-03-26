-- EAFW FloodWatch - Initialize Database
-- Creates schemas, roles, and PostGIS extension

-- ============================================
-- SCHEMAS
-- ============================================
-- gha: Geospatial data (boundaries, rivers, grids, forecasts)
-- cms: Django/Wagtail CMS tables
CREATE SCHEMA IF NOT EXISTS gha;
CREATE SCHEMA IF NOT EXISTS cms;

-- ============================================
-- POSTGIS EXTENSION IN GHA SCHEMA
-- ============================================
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA gha;

-- ============================================
-- ROLES
-- ============================================
DO $$
BEGIN
    -- MapServer read-only role
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mapuser') THEN
        CREATE ROLE mapuser WITH LOGIN PASSWORD 'mapuser';
    END IF;

    -- General read-only role
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'reader') THEN
        CREATE ROLE reader WITH LOGIN PASSWORD 'reader';
    END IF;

    -- Data ingestion role for jobs
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ingest_user') THEN
        CREATE ROLE ingest_user WITH LOGIN PASSWORD 'ingest_user';
    END IF;
END
$$;

-- ============================================
-- PERMISSIONS
-- ============================================
-- gha schema permissions
GRANT USAGE ON SCHEMA gha TO mapuser;
GRANT USAGE ON SCHEMA gha TO reader;
GRANT ALL PRIVILEGES ON SCHEMA gha TO ingest_user;

-- cms schema permissions (for Django)
GRANT ALL PRIVILEGES ON SCHEMA cms TO ingest_user;

-- ============================================
-- DEFAULT SEARCH PATH FOR ALL CONNECTIONS
-- ============================================
-- Set search_path for main user (works for both geomanager and eafw_user)
DO $$ BEGIN
    EXECUTE format('ALTER ROLE %I SET search_path = cms,gha,public', current_user);
END $$;

-- Set search_path for other roles (gha first for geo-focused services)
ALTER ROLE mapuser SET search_path = gha,public;
ALTER ROLE reader SET search_path = gha,public;
ALTER ROLE ingest_user SET search_path = cms,gha,public;

DO $$ BEGIN RAISE NOTICE 'Database initialized: gha + cms schemas, PostGIS, roles, search_path'; END $$;
