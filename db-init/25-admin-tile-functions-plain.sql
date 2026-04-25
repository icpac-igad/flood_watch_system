-- Plain, un-simplified versions of the admin boundary tile functions.
-- (Replaces earlier 25/26 which applied ST_SimplifyPreserveTopology at
-- tile-time.) Now that `gha.admin{0,1,2}` are loaded from the cleaned
-- IGAD-ICPAC parquet source, simplifying at tile-time is no longer needed.

CREATE OR REPLACE FUNCTION gha.admin_clipped(
    z integer,
    x integer,
    y integer,
    admin_level integer DEFAULT 0,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL,
    scope text DEFAULT 'all'
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    mvt bytea;
    tile_env geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    use_whca boolean := (COALESCE(scope, 'all') = 'whca');
BEGIN
    IF admin_level = 1 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
            FROM (SELECT a.country, a.name_1 AS region, ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.whca_admin1 a WHERE a.geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
            FROM (SELECT a.country, a.name_1 AS region, ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.admin1 a WHERE a.geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
    ELSIF admin_level = 2 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
            FROM (SELECT a.country, a.name_1 AS region, a.name_2 AS district, ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.whca_admin2 a WHERE a.geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
            FROM (SELECT a.country, a.name_1 AS region, a.name_2 AS district, ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.admin2 a WHERE a.geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
    ELSE
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
            FROM (SELECT a.country, ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.whca_admin0 a WHERE a.geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
            FROM (SELECT a.country, ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.admin0 a WHERE a.geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
    END IF;
    RETURN COALESCE(mvt, '');
END;
$function$;


CREATE OR REPLACE FUNCTION gha.admin_overlay(
    z integer,
    x integer,
    y integer,
    scope text DEFAULT 'all'
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    out_mvt bytea := '';
    tile_env geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    use_whca boolean := (COALESCE(scope, 'all') = 'whca');
    level_mvt bytea;
BEGIN
    IF use_whca THEN
        SELECT ST_AsMVT(t, 'admin0', 4096, 'mvt_geom') INTO level_mvt
        FROM (SELECT country, ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.whca_admin0 WHERE geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(t, 'admin0', 4096, 'mvt_geom') INTO level_mvt
        FROM (SELECT country, ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.admin0 WHERE geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
    END IF;
    out_mvt := out_mvt || COALESCE(level_mvt, '');

    IF z >= 6 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin1', 4096, 'mvt_geom') INTO level_mvt
            FROM (SELECT country, name_1 AS region, ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.whca_admin1 WHERE geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin1', 4096, 'mvt_geom') INTO level_mvt
            FROM (SELECT country, name_1 AS region, ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.admin1 WHERE geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');
    END IF;

    IF z >= 8 THEN
        IF use_whca THEN
            SELECT ST_AsMVT(t, 'admin2', 4096, 'mvt_geom') INTO level_mvt
            FROM (SELECT country, name_1 AS region, name_2 AS district, ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.whca_admin2 WHERE geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        ELSE
            SELECT ST_AsMVT(t, 'admin2', 4096, 'mvt_geom') INTO level_mvt
            FROM (SELECT country, name_1 AS region, name_2 AS district, ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom FROM gha.admin2 WHERE geom && tile_bbox) t WHERE t.mvt_geom IS NOT NULL;
        END IF;
        out_mvt := out_mvt || COALESCE(level_mvt, '');
    END IF;

    RETURN out_mvt;
END;
$function$;
