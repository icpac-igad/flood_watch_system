from django.db import migrations


FORWARD_SQL = """
-- =================================================================
-- Fix 1: clip_geom_to_admin_extent — strip non-polygon geometries
-- =================================================================
-- ST_Intersection of polygons sharing borders produces
-- GeometryCollections containing stray LineStrings/Points alongside
-- the actual polygon.  These cause rendering artefacts ("stripey"
-- boundaries) in MVT tiles.
--
-- Solution: after every ST_Intersection, extract only polygons
-- using ST_CollectionExtract(..., 3).
-- =================================================================

CREATE OR REPLACE FUNCTION gha.clip_geom_to_admin_extent(
    input_geom geometry,
    clip_geom geometry
)
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    geom_4326 geometry;
    clip_4326 geometry;
    geom_valid geometry;
    clip_valid geometry;
    clipped geometry;
BEGIN
    IF input_geom IS NULL OR clip_geom IS NULL OR ST_IsEmpty(clip_geom) THEN
        RETURN NULL;
    END IF;

    geom_4326 := CASE
        WHEN ST_SRID(input_geom) = 4326 THEN input_geom
        WHEN ST_SRID(input_geom) = 0 THEN ST_SetSRID(input_geom, 4326)
        ELSE ST_Transform(input_geom, 4326)
    END;

    clip_4326 := CASE
        WHEN ST_SRID(clip_geom) = 4326 THEN clip_geom
        WHEN ST_SRID(clip_geom) = 0 THEN ST_SetSRID(clip_geom, 4326)
        ELSE ST_Transform(clip_geom, 4326)
    END;

    IF NOT ST_Intersects(geom_4326, clip_4326) THEN
        RETURN NULL;
    END IF;

    geom_valid := CASE WHEN ST_IsValid(geom_4326) THEN geom_4326 ELSE ST_MakeValid(geom_4326) END;
    clip_valid := CASE WHEN ST_IsValid(clip_4326) THEN clip_4326 ELSE ST_MakeValid(clip_4326) END;

    clipped := ST_Intersection(geom_valid, clip_valid);
    IF clipped IS NULL OR ST_IsEmpty(clipped) THEN
        RETURN NULL;
    END IF;

    -- Extract only polygon geometries (type 3), dropping stray lines/points
    clipped := ST_CollectionExtract(clipped, 3);
    IF clipped IS NULL OR ST_IsEmpty(clipped) THEN
        RETURN NULL;
    END IF;

    RETURN ST_MakeValid(clipped);
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$function$;


-- =================================================================
-- Fix 2: resolve_scope_extent_geom — same CollectionExtract fix
-- =================================================================
CREATE OR REPLACE FUNCTION gha.resolve_scope_extent_geom(
    scope_mode text DEFAULT NULL,
    project_countries text DEFAULT NULL,
    country_name text DEFAULT NULL,
    region_name text DEFAULT NULL,
    district_name text DEFAULT NULL
)
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    normalized_scope text := lower(COALESCE(NULLIF(trim(scope_mode), ''), 'all'));
    scope_geom geometry;
    admin_geom geometry;
    has_admin_filter boolean := (
        (country_name IS NOT NULL AND trim(country_name) <> '')
        OR (region_name IS NOT NULL AND trim(region_name) <> '')
        OR (district_name IS NOT NULL AND trim(district_name) <> '')
    );
    countries_arr text[];
    whca_countries text[] := gha.get_whca_countries();
    result_geom geometry;
BEGIN
    admin_geom := gha.resolve_admin_extent_geom(country_name, region_name, district_name);

    IF normalized_scope = 'all' AND (project_countries IS NULL OR trim(project_countries) = '') THEN
        RETURN admin_geom;
    END IF;

    IF normalized_scope = 'whca' THEN
        scope_geom := gha.resolve_whca_extent_geom();
    ELSIF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        countries_arr := regexp_split_to_array(project_countries, '\\s*,\\s*');

        SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO scope_geom
        FROM gha.admin0
        WHERE country = ANY(countries_arr);
    ELSE
        scope_geom := gha.resolve_admin_extent_geom(NULL, NULL, NULL);
    END IF;

    IF scope_geom IS NULL OR ST_IsEmpty(scope_geom) THEN
        RETURN admin_geom;
    END IF;

    IF NOT has_admin_filter THEN
        RETURN ST_Multi(ST_MakeValid(scope_geom));
    END IF;

    IF admin_geom IS NULL OR ST_IsEmpty(admin_geom) THEN
        RETURN NULL;
    END IF;

    IF normalized_scope = 'whca'
       AND country_name IS NOT NULL
       AND trim(country_name) <> ''
       AND NOT EXISTS (
           SELECT 1
           FROM unnest(whca_countries) AS whca(country)
           WHERE lower(trim(whca.country)) = lower(trim(country_name))
       ) THEN
        RETURN NULL;
    END IF;

    IF project_countries IS NOT NULL
       AND trim(project_countries) <> ''
       AND country_name IS NOT NULL
       AND trim(country_name) <> ''
       AND NOT EXISTS (
           SELECT 1
           FROM unnest(countries_arr) AS project(country)
           WHERE lower(trim(project.country)) = lower(trim(country_name))
       ) THEN
        RETURN NULL;
    END IF;

    IF ST_Within(admin_geom, scope_geom) THEN
        RETURN ST_Multi(ST_MakeValid(admin_geom));
    END IF;

    IF NOT ST_Intersects(admin_geom, scope_geom) THEN
        RETURN NULL;
    END IF;

    -- Extract only polygon geometries from intersection result
    result_geom := ST_Intersection(admin_geom, scope_geom);
    result_geom := ST_CollectionExtract(result_geom, 3);
    IF result_geom IS NULL OR ST_IsEmpty(result_geom) THEN
        RETURN NULL;
    END IF;

    RETURN ST_Multi(ST_MakeValid(result_geom));
END;
$function$;


-- =================================================================
-- Fix 3: admin_whca — stop clipping admin0 geometry when only
-- country filter is active (no need to clip Ethiopia to itself)
-- =================================================================
DROP FUNCTION IF EXISTS gha.admin_whca(integer, integer, integer, integer, text, text, text);

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
    whca_countries text[] := gha.get_whca_countries();
    has_admin_filter boolean := (
        (country_name IS NOT NULL AND trim(country_name) <> '')
        OR (region_name IS NOT NULL AND trim(region_name) <> '')
        OR (district_name IS NOT NULL AND trim(district_name) <> '')
    );
    -- Only clip admin0 geometry when region/district is set (sub-country filter)
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
                ST_AsMVTGeom(ST_Transform(a.geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1 a
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (NOT has_admin_filter OR (
                  (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
                  AND (region_name IS NULL OR trim(region_name) = '' OR a.name_1 = region_name)
              ))
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
            WHERE a.country = ANY(whca_countries)
              AND a.geom && effective_geom
              AND ST_Intersects(a.geom, effective_geom)
              AND (NOT has_admin_filter OR (
                  (country_name IS NULL OR trim(country_name) = '' OR a.country = country_name)
                  AND (region_name IS NULL OR trim(region_name) = '' OR a.name_1 = region_name)
                  AND (district_name IS NULL OR trim(district_name) = '' OR a.name_2 = district_name)
              ))
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSE
        -- admin0: only clip geometry when sub-country filter is active
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


-- =================================================================
-- Fix 4: admin_clipped — same needs_strict_admin0_clip pattern
-- =================================================================
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

GRANT EXECUTE ON FUNCTION gha.admin_clipped(integer, integer, integer, integer, text, text, text) TO PUBLIC;


-- =================================================================
-- Fix 5: admin_by_project — same pattern
-- =================================================================
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

GRANT EXECUTE ON FUNCTION gha.admin_by_project(integer, integer, integer, integer, text, text, text, text) TO PUBLIC;


-- =================================================================
-- Performance: add missing indexes for faster tile & API queries
-- =================================================================

-- Compound index for admin lookups (country + region)
CREATE INDEX IF NOT EXISTS idx_gha_admin0_country
    ON gha.admin0 (country);
CREATE INDEX IF NOT EXISTS idx_gha_admin1_country_name1
    ON gha.admin1 (country, name_1);
CREATE INDEX IF NOT EXISTS idx_gha_admin2_country_name1_name2
    ON gha.admin2 (country, name_1, name_2);

-- Control points: WHCA filter and coordinate-based clustering
CREATE INDEX IF NOT EXISTS idx_control_points_whca
    ON gha.multimodal_control_points (whca_selected)
    WHERE whca_selected = true;

-- Forecast lookups: index by date for faster recent-window scans.
-- Note: partial index predicates must be IMMUTABLE; CURRENT_DATE is not.
CREATE INDEX IF NOT EXISTS idx_mm_forecasts_data_date
    ON gha.multimodal_forecasts (data_date DESC);

-- ANALYZE to update planner statistics
ANALYZE gha.multimodal_forecasts;
ANALYZE gha.multimodal_control_points;
ANALYZE gha.admin0;
ANALYZE gha.admin1;
ANALYZE gha.admin2;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0070_include_eritrea_in_admin_boundaries"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
