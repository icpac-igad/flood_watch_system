from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0038_add_unmanaged_expert_assessment_models"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE OR REPLACE FUNCTION gha.admin_whca(
    z integer,
    x integer,
    y integer,
    admin_level integer DEFAULT 0
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
    whca_countries text[] := ARRAY['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    IF admin_level = 0 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id AS gid,
                gid_0,
                country,
                shape_area,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin0
            WHERE geom && tile_bbox_4326
              AND country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 1 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id AS gid,
                gid_0,
                country,
                gid_1,
                name_1 AS region,
                type_1,
                shape_area,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin1
            WHERE geom && tile_bbox_4326
              AND country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;

    ELSIF admin_level = 2 THEN
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id AS gid,
                gid_0,
                country,
                gid_1,
                name_1 AS region,
                gid_2,
                name_2 AS district,
                type_2,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin2
            WHERE geom && tile_bbox_4326
              AND country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    ELSE
        SELECT ST_AsMVT(tile, 'gha.admin_whca', 4096, 'mvt_geom') INTO mvt
        FROM (
            SELECT
                id AS gid,
                gid_0,
                country,
                shape_area,
                ST_AsMVTGeom(ST_Transform(geom, 3857), tile_bbox_3857, 4096, 64, true) AS mvt_geom
            FROM gha.admin0
            WHERE geom && tile_bbox_4326
              AND country = ANY(whca_countries)
        ) AS tile
        WHERE tile.mvt_geom IS NOT NULL;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.admin_whca(integer, integer, integer, integer) TO PUBLIC;
COMMENT ON FUNCTION gha.admin_whca(integer, integer, integer, integer)
IS 'WHCA admin boundary tiles (Uganda, Rwanda, South Sudan, Ethiopia, Sudan). Parameters: admin_level (0=country, 1=region, 2=district).';
            """,
            reverse_sql=migrations.RunSQL.noop,
        )
    ]
