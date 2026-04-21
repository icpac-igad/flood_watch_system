-- ============================================================================
-- Re-enrich gha.multimodal_control_points admin labels from the new admin
-- tables via spatial lookup. Also expose a stable per-point "admin label"
-- that every UI (chart title, popup, API) can use deterministically.
--
-- Fields added / refreshed:
--   admin_name   — "{COUNTRY}{NAME_1}{NAME_2}" derived from admin2 intersection
--   gid_2        — GADM level-2 id for the polygon containing the point
--   gid_1        — GADM level-1 id
--   gid_0        — GADM level-0 (country ISO-3) id
--
-- Leaves point_id as the canonical PK (unchanged); the enriched admin_name
-- becomes a human-readable secondary label.
-- ============================================================================

-- Make sure the target columns exist (idempotent)
ALTER TABLE gha.multimodal_control_points
    ADD COLUMN IF NOT EXISTS gid_0 TEXT,
    ADD COLUMN IF NOT EXISTS gid_1 TEXT,
    ADD COLUMN IF NOT EXISTS gid_2 TEXT;

-- Refresh from admin2 using spatial containment. Falls back to admin1 then
-- admin0 for points that happen to land outside admin2 coverage (shouldn't
-- normally happen but keeps the query safe).
WITH enriched AS (
    SELECT cp.point_id,
           COALESCE(a2.gid_0, a1.gid_0, a0.gid_0)                  AS gid_0,
           COALESCE(a2.gid_1, a1.gid_1)                            AS gid_1,
           a2.gid_2                                                 AS gid_2,
           -- Compose a human-readable label
           COALESCE(
               CONCAT_WS('', UPPER(a2.gid_0), a2.name_1, a2.name_2),
               CONCAT_WS('', UPPER(a1.gid_0), a1.name_1),
               a0.country
           ) AS admin_name
    FROM gha.multimodal_control_points cp
    LEFT JOIN gha.admin2 a2 ON ST_Within(cp.geom, a2.geom)
    LEFT JOIN gha.admin1 a1 ON a2.gid_0 IS NULL AND ST_Within(cp.geom, a1.geom)
    LEFT JOIN gha.admin0 a0 ON a2.gid_0 IS NULL AND a1.gid_0 IS NULL AND ST_Within(cp.geom, a0.geom)
)
UPDATE gha.multimodal_control_points cp
SET admin_name = e.admin_name,
    gid_0      = e.gid_0,
    gid_1      = e.gid_1,
    gid_2      = e.gid_2
FROM enriched e
WHERE cp.point_id = e.point_id;

-- Fallback: for points that fell outside admin2 containment (e.g. on lakes
-- or coastlines), snap to the NEAREST admin2 polygon — no distance cap so
-- every point ends up with *some* label.
WITH bad AS (
    SELECT point_id, geom
    FROM gha.multimodal_control_points
    WHERE admin_name IS NULL OR admin_name = '' OR admin_name ~ '^[0-9]+$'
),
nearest AS (
    SELECT b.point_id,
           (SELECT gid_0  FROM gha.admin2 a2 ORDER BY a2.geom <-> b.geom LIMIT 1) AS gid_0,
           (SELECT gid_1  FROM gha.admin2 a2 ORDER BY a2.geom <-> b.geom LIMIT 1) AS gid_1,
           (SELECT gid_2  FROM gha.admin2 a2 ORDER BY a2.geom <-> b.geom LIMIT 1) AS gid_2,
           (SELECT name_1 FROM gha.admin2 a2 ORDER BY a2.geom <-> b.geom LIMIT 1) AS name_1,
           (SELECT name_2 FROM gha.admin2 a2 ORDER BY a2.geom <-> b.geom LIMIT 1) AS name_2
    FROM bad b
)
UPDATE gha.multimodal_control_points cp
SET gid_0      = n.gid_0,
    gid_1      = n.gid_1,
    gid_2      = n.gid_2,
    admin_name = CONCAT_WS('', UPPER(n.gid_0), n.name_1, n.name_2)
FROM nearest n
WHERE cp.point_id = n.point_id;

-- Reporting
SELECT
    COUNT(*) AS total_points,
    COUNT(*) FILTER (WHERE admin_name IS NULL OR admin_name = '' OR admin_name ~ '^[0-9]+$')
         AS still_missing_label,
    COUNT(*) FILTER (WHERE gid_2 IS NOT NULL) AS have_gid_2,
    COUNT(DISTINCT gid_0) AS distinct_countries
FROM gha.multimodal_control_points;
