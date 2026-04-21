-- ============================================================================
-- Dissolved admin boundaries — fixes visible double-drawing of shared borders
-- (e.g. Kenya / South Sudan).
--
-- Each country polygon currently contributes its full outline, so a border
-- shared between two countries is rendered twice → "thick" / jagged look.
-- We precompute the UnaryUnion'd border (one linestring per unique edge) in
-- materialized views that the admin_overlay function serves alongside the
-- polygons (which we keep for click interaction).
--
-- ST_SimplifyPreserveTopology(0.001°) trims vertex density while keeping
-- neighbours aligned (coincident vertices stay coincident).
-- ============================================================================

-- ── Derive all borders from admin2 (finest unit) so admin1 and admin0
--    share the EXACT same edges where they coincide. ST_SnapToGrid aligns
--    vertex coordinates to a 0.0001° grid (~11m) before dissolving so
--    cross-level edges hit exactly the same coordinates. ──────────────────

-- all-GHA: first build a snapped copy of admin2 once, then dissolve upward
DROP MATERIALIZED VIEW IF EXISTS gha.admin2_border CASCADE;
CREATE MATERIALIZED VIEW gha.admin2_border AS
WITH snapped AS (
    SELECT country, name_1, name_2,
           ST_MakeValid(ST_SnapToGrid(geom, 0.0001)) AS geom
    FROM gha.admin2
)
SELECT ST_Boundary(ST_UnaryUnion(ST_Collect(geom))) AS geom
FROM snapped;

DROP MATERIALIZED VIEW IF EXISTS gha.admin1_border CASCADE;
CREATE MATERIALIZED VIEW gha.admin1_border AS
WITH snapped AS (
    SELECT country, name_1,
           ST_MakeValid(ST_SnapToGrid(geom, 0.0001)) AS geom
    FROM gha.admin2
),
dissolved_by_region AS (
    SELECT country, name_1, ST_UnaryUnion(ST_Collect(geom)) AS geom
    FROM snapped
    GROUP BY country, name_1
),
merged AS (
    SELECT ST_Boundary(ST_UnaryUnion(ST_Collect(geom))) AS geom
    FROM dissolved_by_region
)
SELECT ST_SimplifyPreserveTopology(geom, 0.003) AS geom FROM merged;

DROP MATERIALIZED VIEW IF EXISTS gha.admin0_border CASCADE;
CREATE MATERIALIZED VIEW gha.admin0_border AS
WITH snapped AS (
    SELECT country,
           ST_MakeValid(ST_SnapToGrid(geom, 0.0001)) AS geom
    FROM gha.admin2
),
dissolved_by_country AS (
    SELECT country, ST_UnaryUnion(ST_Collect(geom)) AS geom
    FROM snapped
    GROUP BY country
),
merged AS (
    SELECT ST_Boundary(ST_UnaryUnion(ST_Collect(geom))) AS geom
    FROM dissolved_by_country
)
-- Heaviest simplification for country borders (smooth coastlines etc.)
SELECT ST_SimplifyPreserveTopology(geom, 0.01) AS geom FROM merged;

-- whca scope borders — same pattern
DROP MATERIALIZED VIEW IF EXISTS gha.whca_admin2_border CASCADE;
CREATE MATERIALIZED VIEW gha.whca_admin2_border AS
WITH snapped AS (
    SELECT country, name_1, name_2,
           ST_MakeValid(ST_SnapToGrid(geom, 0.0001)) AS geom
    FROM gha.whca_admin2
)
SELECT ST_Boundary(ST_UnaryUnion(ST_Collect(geom))) AS geom
FROM snapped;

DROP MATERIALIZED VIEW IF EXISTS gha.whca_admin1_border CASCADE;
CREATE MATERIALIZED VIEW gha.whca_admin1_border AS
WITH snapped AS (
    SELECT country, name_1,
           ST_MakeValid(ST_SnapToGrid(geom, 0.0001)) AS geom
    FROM gha.whca_admin2
),
dissolved_by_region AS (
    SELECT country, name_1, ST_UnaryUnion(ST_Collect(geom)) AS geom
    FROM snapped
    GROUP BY country, name_1
),
merged AS (
    SELECT ST_Boundary(ST_UnaryUnion(ST_Collect(geom))) AS geom
    FROM dissolved_by_region
)
SELECT ST_SimplifyPreserveTopology(geom, 0.003) AS geom FROM merged;

DROP MATERIALIZED VIEW IF EXISTS gha.whca_admin0_border CASCADE;
CREATE MATERIALIZED VIEW gha.whca_admin0_border AS
WITH snapped AS (
    SELECT country,
           ST_MakeValid(ST_SnapToGrid(geom, 0.0001)) AS geom
    FROM gha.whca_admin2
),
dissolved_by_country AS (
    SELECT country, ST_UnaryUnion(ST_Collect(geom)) AS geom
    FROM snapped
    GROUP BY country
),
merged AS (
    SELECT ST_Boundary(ST_UnaryUnion(ST_Collect(geom))) AS geom
    FROM dissolved_by_country
)
SELECT ST_SimplifyPreserveTopology(geom, 0.01) AS geom FROM merged;

-- ── spatial indexes for fast tile queries ───────────────────────────────
CREATE INDEX IF NOT EXISTS admin0_border_geom_idx      ON gha.admin0_border      USING GIST (geom);
CREATE INDEX IF NOT EXISTS admin1_border_geom_idx      ON gha.admin1_border      USING GIST (geom);
CREATE INDEX IF NOT EXISTS admin2_border_geom_idx      ON gha.admin2_border      USING GIST (geom);
CREATE INDEX IF NOT EXISTS whca_admin0_border_geom_idx ON gha.whca_admin0_border USING GIST (geom);
CREATE INDEX IF NOT EXISTS whca_admin1_border_geom_idx ON gha.whca_admin1_border USING GIST (geom);
CREATE INDEX IF NOT EXISTS whca_admin2_border_geom_idx ON gha.whca_admin2_border USING GIST (geom);


-- ============================================================================
-- Replace gha.admin_overlay so each zoom-level emits BOTH:
--   • an "admin{N}" source-layer (polygons — used for invisible fill/click)
--   • an "admin{N}_border" source-layer (dissolved linestring — used for
--     visible stroke, shared edges drawn exactly once)
-- ============================================================================

CREATE OR REPLACE FUNCTION gha.admin_overlay(
    z integer, x integer, y integer,
    scope text DEFAULT 'all'
) RETURNS bytea
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    out_mvt bytea := '';
    tile_env  geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    use_whca  boolean  := (COALESCE(scope, 'all') = 'whca');
    level_mvt bytea;
BEGIN
    -- ── admin0 (always) ──────────────────────────────────────────────
    -- polygons (for click/fill)
    IF use_whca THEN
        SELECT ST_AsMVT(t, 'admin0', 4096, 'mvt_geom') INTO level_mvt FROM (
            SELECT country,
                   ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
            FROM gha.whca_admin0 WHERE geom && tile_bbox
        ) t WHERE t.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(t, 'admin0', 4096, 'mvt_geom') INTO level_mvt FROM (
            SELECT country,
                   ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
            FROM gha.admin0 WHERE geom && tile_bbox
        ) t WHERE t.mvt_geom IS NOT NULL;
    END IF;
    out_mvt := out_mvt || COALESCE(level_mvt, '');

    -- dissolved borders (for display) — only renders shared edges once
    IF use_whca THEN
        SELECT ST_AsMVT(t, 'admin0_border', 4096, 'mvt_geom') INTO level_mvt FROM (
            SELECT ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
            FROM gha.whca_admin0_border WHERE geom && tile_bbox
        ) t WHERE t.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(t, 'admin0_border', 4096, 'mvt_geom') INTO level_mvt FROM (
            SELECT ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
            FROM gha.admin0_border WHERE geom && tile_bbox
        ) t WHERE t.mvt_geom IS NOT NULL;
    END IF;
    out_mvt := out_mvt || COALESCE(level_mvt, '');

    -- ── admin1 (z >= 6) ──────────────────────────────────────────────
    IF z >= 6 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin1', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT country, name_1 AS region,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.whca_admin1 WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin1', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT country, name_1 AS region,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.admin1 WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');

        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin1_border', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.whca_admin1_border WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin1_border', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.admin1_border WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');
    END IF;

    -- ── admin2 (z >= 8) ──────────────────────────────────────────────
    IF z >= 8 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin2', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT country, name_1 AS region, name_2 AS district,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.whca_admin2 WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin2', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT country, name_1 AS region, name_2 AS district,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.admin2 WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');

        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin2_border', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.whca_admin2_border WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin2_border', 4096, 'mvt_geom') INTO level_mvt FROM (
                SELECT ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.admin2_border WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');
    END IF;

    RETURN out_mvt;
END;
$$;


-- ============================================================================
-- Helper to refresh borders if the underlying admin* tables change.
-- Run manually: SELECT gha.refresh_admin_borders();
-- ============================================================================
CREATE OR REPLACE FUNCTION gha.refresh_admin_borders() RETURNS TEXT
LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW gha.admin0_border;
    REFRESH MATERIALIZED VIEW gha.admin1_border;
    REFRESH MATERIALIZED VIEW gha.admin2_border;
    REFRESH MATERIALIZED VIEW gha.whca_admin0_border;
    REFRESH MATERIALIZED VIEW gha.whca_admin1_border;
    REFRESH MATERIALIZED VIEW gha.whca_admin2_border;
    RETURN 'refreshed 6 border views';
END;
$$;
