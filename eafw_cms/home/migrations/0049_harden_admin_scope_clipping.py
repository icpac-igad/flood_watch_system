from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0048_add_scope_clipping_functions"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
DROP FUNCTION IF EXISTS gha.admin_by_project(integer, integer, integer, integer, text);

CREATE OR REPLACE FUNCTION gha.admin_by_project(
    z integer,
    x integer,
    y integer,
    admin_level integer DEFAULT 0,
    project_countries text DEFAULT NULL,
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
    needs_strict_admin0_clip boolean := (
        (region_name IS NOT NULL AND trim(region_name) <> '')
        OR (district_name IS NOT NULL AND trim(district_name) <> '')
    );
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    scope_geom := gha.resolve_scope_extent_geom(
        'project',
        project_countries,
        country_name,
        region_name,
        district_name
    );
    effective_geom := gha.clip_geom_to_admin_extent(tile_bbox_4326, scope_geom);

    IF effective_geom IS NULL OR ST_IsEmpty(effective_geom) THEN
        RETURN ''::bytea;
    END IF;

    IF admin_level = 1 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_by_project', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.gid_1,
                a.name_1 AS region,
                a.type_1,
                a.shape_area,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSIF admin_level = 2 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_by_project', 4096, 'mvt_geom') INTO mvt
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
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin2 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.admin_by_project', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.id AS gid,
                a.gid_0,
                a.country,
                a.shape_area,
                ST_AsMVTGeom(
                    ST_Transform(
                        CASE
                            WHEN needs_strict_admin0_clip THEN gha.clip_geom_to_admin_extent(a.geom, effective_geom)
                            ELSE a.geom
                        END,
                        3857
                    ),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin0 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

CREATE OR REPLACE FUNCTION gha.admin_clipped(
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
    needs_strict_admin0_clip boolean := (
        (region_name IS NOT NULL AND trim(region_name) <> '')
        OR (district_name IS NOT NULL AND trim(district_name) <> '')
    );
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    scope_geom := gha.resolve_scope_extent_geom(
        'all',
        NULL,
        country_name,
        region_name,
        district_name
    );
    effective_geom := gha.clip_geom_to_admin_extent(tile_bbox_4326, scope_geom);

    IF effective_geom IS NULL OR ST_IsEmpty(effective_geom) THEN
        RETURN ''::bytea;
    END IF;

    IF admin_level = 1 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.country,
                a.name_1 AS region,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSIF admin_level = 2 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.country,
                a.name_1 AS region,
                a.name_2 AS district,
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin2 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.admin_clipped', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                a.country,
                ST_AsMVTGeom(
                    ST_Transform(
                        CASE
                            WHEN needs_strict_admin0_clip THEN gha.clip_geom_to_admin_extent(a.geom, effective_geom)
                            ELSE a.geom
                        END,
                        3857
                    ),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin0 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

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
    needs_strict_admin0_clip boolean := (
        (region_name IS NOT NULL AND trim(region_name) <> '')
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
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND a.country = ANY(whca_countries)
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
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin2 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND a.country = ANY(whca_countries)
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
                        CASE
                            WHEN needs_strict_admin0_clip THEN gha.clip_geom_to_admin_extent(a.geom, effective_geom)
                            ELSE a.geom
                        END,
                        3857
                    ),
                    tile_bbox_3857,
                    4096,
                    64,
                    true
                ) AS mvt_geom
            FROM gha.admin0 a
            WHERE a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND a.country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.admin_by_project(integer, integer, integer, integer, text, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.admin_clipped(integer, integer, integer, integer, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.admin_whca(integer, integer, integer, integer, text, text, text) TO PUBLIC;

COMMENT ON FUNCTION gha.admin_by_project(integer, integer, integer, integer, text, text, text, text)
IS 'Project-scoped admin boundary tiles clipped to scope and optional country/region/district filters.';
COMMENT ON FUNCTION gha.admin_clipped(integer, integer, integer, integer, text, text, text)
IS 'Admin boundary tiles clipped to admin scope for admin0/admin1/admin2.';
COMMENT ON FUNCTION gha.admin_whca(integer, integer, integer, integer, text, text, text)
IS 'WHCA admin boundary tiles clipped to scope and optional country/region/district filters.';
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
