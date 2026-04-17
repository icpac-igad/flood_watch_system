-- Overlay admin boundaries function:
-- Always returns admin0; adds admin1 when z>=6; adds admin2 when z>=8.
-- Each level is emitted as a distinct MVT layer so the frontend can style
-- them independently with different line widths/colors and minzoom filters.
--
-- Frontend uses source-layer names: "admin0", "admin1", "admin2".
-- Scope-aware: when scope='whca', uses gha.whca_admin0/1/2 tables.

CREATE OR REPLACE FUNCTION gha.admin_overlay(
    z integer, x integer, y integer,
    scope text DEFAULT 'all'
) RETURNS bytea
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    out_mvt bytea := '';
    tile_env geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    use_whca boolean := (COALESCE(scope, 'all') = 'whca');
    level_mvt bytea;
BEGIN
    -- admin0: always included
    IF use_whca THEN
        SELECT ST_AsMVT(t, 'admin0', 4096, 'mvt_geom') INTO level_mvt
        FROM (
            SELECT country,
                   ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
            FROM gha.whca_admin0
            WHERE geom && tile_bbox
        ) t WHERE t.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(t, 'admin0', 4096, 'mvt_geom') INTO level_mvt
        FROM (
            SELECT country,
                   ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
            FROM gha.admin0
            WHERE geom && tile_bbox
        ) t WHERE t.mvt_geom IS NOT NULL;
    END IF;
    out_mvt := out_mvt || COALESCE(level_mvt, '');

    -- admin1: z >= 6
    IF z >= 6 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin1', 4096, 'mvt_geom') INTO level_mvt
            FROM (
                SELECT country, name_1 AS region,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.whca_admin1
                WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin1', 4096, 'mvt_geom') INTO level_mvt
            FROM (
                SELECT country, name_1 AS region,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.admin1
                WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');
    END IF;

    -- admin2: z >= 8
    IF z >= 8 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin2', 4096, 'mvt_geom') INTO level_mvt
            FROM (
                SELECT country, name_1 AS region, name_2 AS district,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.whca_admin2
                WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin2', 4096, 'mvt_geom') INTO level_mvt
            FROM (
                SELECT country, name_1 AS region, name_2 AS district,
                       ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
                FROM gha.admin2
                WHERE geom && tile_bbox
            ) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');
    END IF;

    RETURN out_mvt;
END;
$$;
