-- Initialize EAFW MapServer Database
-- Run all schema, table, and function scripts in order

-- Create roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mapuser') THEN
        CREATE ROLE mapuser WITH LOGIN PASSWORD 'mapuser';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'reader') THEN
        CREATE ROLE reader WITH LOGIN PASSWORD 'reader';
    END IF;
END
$$;

-- Source schemas
\i /docker-entrypoint-initdb.d/schemas/01-alerts-schema.sql
\i /docker-entrypoint-initdb.d/schemas/02-grids-schema.sql

-- Source functions
\i /docker-entrypoint-initdb.d/functions/01-create-fishnet.sql

-- Source tables
\i /docker-entrypoint-initdb.d/tables/01-grid-01dd.sql
\i /docker-entrypoint-initdb.d/tables/02-daily-alerts.sql

-- Source query functions (after tables exist)
\i /docker-entrypoint-initdb.d/functions/02-get-daily-alerts.sql
