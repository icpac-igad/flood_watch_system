CREATE OR REPLACE FUNCTION gha.admin_whca(
    z integer,
    x integer,
    y integer,
    admin_level integer DEFAULT 0,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    mvt bytea;
    tile_bbox_3857 geometry;
    tile_bbox_4326 geometry;
    scope_geom geometry;
    effective_geom geometry;
    whca_countries text[] := ARRAY['Sudan', 'South Sudan', 'Uganda', 'Ethiopia', 'Rwanda'];
    has_admin_filter boolean := (
        (country_name IS NOT NULL AND trim(country_name) <> '')
        OR (region_name IS NOT NULL AND trim(region_name) <> '')
        OR (district_name IS NOT NULL AND trim(district_name) <> '')
    );
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    scope_geom := gha.resolve_scope_extent_geom(
        'whca',
        NULL,
        country_name,
        region_name,
        district_name
    );

    IF scope_geom IS NULL OR ST_IsEmpty(scope_geom) THEN
        RETURN ''::bytea;
    END IF;

    effective_geom := gha.clip_geom_to_admin_extent(tile_bbox_4326, scope_geom);

    IF effective_geom IS NULL OR ST_IsEmpty(effective_geom) THEN
        RETURN ''::bytea;
    END IF;

    IF admin_level = 1 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.gid_1,
                a.name_1 AS region,
                a.type_1,
                a.shape_area,
                ST_AsMVTGeom(
                    ST_Transform(gha.clip_geom_to_admin_extent(a.geom, effective_geom), 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin1 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (
                  NOT has_admin_filter OR (
                      (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
                      AND (region_name IS NULL OR trim(region_name) = '' OR a.name_1 = region_name)
                  )
              )
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 2 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.gid_1,
                a.name_1 AS region,
                a.gid_2,
                a.name_2 AS district,
                a.type_2,
                a.shape_area,
                ST_AsMVTGeom(
                    ST_Transform(gha.clip_geom_to_admin_extent(a.geom, effective_geom), 3857),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin2 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (
                  NOT has_admin_filter OR (
                      (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
                      AND (region_name IS NULL OR trim(region_name) = '' OR a.name_1 = region_name)
                      AND (district_name IS NULL OR trim(district_name) = '' OR a.name_2 = district_name)
                  )
              )
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSE
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.shape_area,
                ST_AsMVTGeom(
                    ST_Transform(
                        gha.clip_geom_to_admin_extent(a.geom, effective_geom),
                        3857
                    ),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin0 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.admin_whca(integer, integer, integer, integer, text, text, text) TO PUBLIC;
