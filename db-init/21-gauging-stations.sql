-- ============================================================================
-- Ingest curated gauging-station points as station_type='gauging' in
-- gha.multimodal_control_points, and fix earlier Rwanda admin mislabels.
--
-- Source: /db-init/21-gauging-stations.csv (78 rows, 5 countries)
--   ET=41, UG=13, RW=10, SD=9, SS=5
--
-- Behaviour:
--   - Adds station_name / station_river / station_basin columns (idempotent).
--   - For existing points snapped to the same lat/lon within ~10 m
--     (already-ingested Rwanda, 3200-3209), UPDATE station_name/river/basin
--     and re-enrich admin_name using a country-code-filtered join so points
--     on national borders don't slip across (fixes 3203 Kagitumba labelled
--     as Uganda Ntungamo).
--   - For the remaining rows (any shapefile station that doesn't match an
--     existing point within 10 m), INSERT as NEW gauging points, with
--     admin_name enriched against the right country's admin2 polygon.
--
-- Re-running this migration is safe: matches are by coordinate, so reloads
-- UPDATE the same rows instead of duplicating.
-- ============================================================================

ALTER TABLE gha.multimodal_control_points
    ADD COLUMN IF NOT EXISTS station_name  TEXT,
    ADD COLUMN IF NOT EXISTS station_river TEXT,
    ADD COLUMN IF NOT EXISTS station_basin TEXT;

-- Stage the CSV in a throwaway table; dropped at end of migration.
DROP TABLE IF EXISTS gha._gauging_staging;
CREATE TABLE gha._gauging_staging (
    country_code TEXT,
    station_name TEXT,
    river        TEXT,
    basin        TEXT,
    lon          DOUBLE PRECISION,
    lat          DOUBLE PRECISION,
    geom         geometry(Point, 4326)
);

\copy gha._gauging_staging(country_code, station_name, river, basin, lon, lat) FROM '/db-init/21-gauging-stations.csv' WITH (FORMAT csv, HEADER true)

UPDATE gha._gauging_staging
SET    geom = ST_SetSRID(ST_MakePoint(lon, lat), 4326);

-- Resolve ISO-2 (DB) → ISO-3 (admin tables)
CREATE TEMP TABLE _iso2_to_iso3 (iso2 TEXT PRIMARY KEY, iso3 TEXT) ON COMMIT DROP;
INSERT INTO _iso2_to_iso3 VALUES
    ('ET','ETH'), ('UG','UGA'), ('RW','RWA'), ('SD','SDN'), ('SS','SSD'),
    ('KE','KEN'), ('TZ','TZA'), ('BI','BDI'), ('SO','SOM'), ('DJ','DJI'), ('ER','ERI');

-- Country-filtered admin enrichment: intersect with admin2 of THIS country
-- only, so a point on the RW/UG border gets the Rwanda polygon instead of
-- snapping across. Falls back to nearest admin2 within the same country if
-- containment fails (e.g. coordinate just outside the polygon).
CREATE TEMP TABLE _resolved ON COMMIT DROP AS
SELECT s.country_code,
       s.station_name,
       s.river,
       s.basin,
       s.lon,
       s.lat,
       s.geom,
       c.iso3,
       COALESCE(a2.gid_0, nn.gid_0)                 AS gid_0,
       COALESCE(a2.gid_1, nn.gid_1)                 AS gid_1,
       COALESCE(a2.gid_2, nn.gid_2)                 AS gid_2,
       CONCAT_WS('',
           UPPER(COALESCE(a2.gid_0, nn.gid_0)),
           COALESCE(a2.name_1, nn.name_1),
           COALESCE(a2.name_2, nn.name_2)
       )                                            AS admin_name
FROM   gha._gauging_staging s
JOIN   _iso2_to_iso3 c ON c.iso2 = s.country_code
LEFT JOIN LATERAL (
    SELECT a.gid_0, a.gid_1, a.gid_2, a.name_1, a.name_2
    FROM   gha.admin2 a
    WHERE  a.gid_0 = c.iso3
      AND  ST_Within(s.geom, a.geom)
    LIMIT 1
) a2 ON TRUE
LEFT JOIN LATERAL (
    SELECT a.gid_0, a.gid_1, a.gid_2, a.name_1, a.name_2
    FROM   gha.admin2 a
    WHERE  a.gid_0 = c.iso3
    ORDER BY a.geom <-> s.geom
    LIMIT 1
) nn ON a2.gid_0 IS NULL;

-- 1. UPDATE existing points whose geometry is within ~10 m of a staging row.
--    Match on ST_DWithin(..., 0.0001 deg ≈ 11 m at the equator).
WITH match AS (
    SELECT cp.point_id, r.*
    FROM   gha.multimodal_control_points cp
    JOIN   _resolved r
           ON ST_DWithin(cp.geom, r.geom, 0.0001)
)
UPDATE gha.multimodal_control_points cp
SET    station_name  = m.station_name,
       station_river = NULLIF(m.river, ''),
       station_basin = NULLIF(m.basin, ''),
       station_type  = 'gauging',
       country_code  = m.country_code,
       admin_name    = m.admin_name,
       gid_0         = m.gid_0,
       gid_1         = m.gid_1,
       gid_2         = m.gid_2,
       x             = m.lon,
       y             = m.lat,
       geom          = m.geom
FROM   match m
WHERE  cp.point_id = m.point_id;

-- 2. INSERT rows that had no existing point within 10 m, with fresh point_ids
--    continuing from the current MAX.
WITH unmatched AS (
    SELECT r.*
    FROM   _resolved r
    WHERE  NOT EXISTS (
        SELECT 1
        FROM   gha.multimodal_control_points cp
        WHERE  ST_DWithin(cp.geom, r.geom, 0.0001)
    )
),
numbered AS (
    SELECT row_number() OVER (ORDER BY country_code, lat, lon) AS rn, u.*
    FROM   unmatched u
),
base AS (
    SELECT COALESCE(MAX(point_id), 0) AS max_id FROM gha.multimodal_control_points
)
INSERT INTO gha.multimodal_control_points
    (point_id, x, y, geom, country_code, station_type,
     station_name, station_river, station_basin,
     admin_name, gid_0, gid_1, gid_2)
SELECT b.max_id + n.rn,
       n.lon, n.lat, n.geom,
       n.country_code, 'gauging',
       n.station_name, NULLIF(n.river, ''), NULLIF(n.basin, ''),
       n.admin_name, n.gid_0, n.gid_1, n.gid_2
FROM   numbered n, base b;

DROP TABLE gha._gauging_staging;

-- Reporting
SELECT station_type, COUNT(*) FROM gha.multimodal_control_points GROUP BY station_type;
SELECT country_code, COUNT(*) FROM gha.multimodal_control_points
WHERE  station_type = 'gauging'
GROUP  BY country_code
ORDER  BY country_code;
