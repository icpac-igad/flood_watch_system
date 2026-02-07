from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0031_add_icpac_style_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE OR REPLACE FUNCTION gha.clip_to_admin(
    z integer,
    x integer,
    y integer,
    table_name text,
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
    filter_geom geometry;
    schema_name text;
    relation_name text;
    layer_name text;
    sql_query text;
BEGIN
    tile_bbox_3857 := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 := ST_Transform(tile_bbox_3857, 4326);

    schema_name := split_part(table_name, '.', 1);
    relation_name := split_part(table_name, '.', 2);

    IF schema_name = '' OR relation_name = '' THEN
        RAISE EXCEPTION 'table_name must be schema-qualified (schema.table), got: %', table_name;
    END IF;

    layer_name := format('%s.%s', schema_name, relation_name);

    IF district_name IS NOT NULL AND district_name <> '' THEN
        SELECT geom INTO filter_geom
        FROM gha.admin2
        WHERE name_2 = district_name
          AND (region_name IS NULL OR region_name = '' OR name_1 = region_name)
          AND (country_name IS NULL OR country_name = '' OR country = country_name)
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND region_name <> '' THEN
        SELECT geom INTO filter_geom
        FROM gha.admin1
        WHERE name_1 = region_name
          AND (country_name IS NULL OR country_name = '' OR country = country_name)
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND country_name <> '' THEN
        SELECT geom INTO filter_geom
        FROM gha.admin0
        WHERE country = country_name
        LIMIT 1;
    END IF;

    sql_query := format(
        'SELECT ST_AsMVT(tile, %L, 4096, ''mvt_geom'')
         FROM (
             SELECT t.*, ST_AsMVTGeom(ST_Transform(t.geom, 3857), $1, 4096, 64, true) AS mvt_geom
             FROM %I.%I t
             WHERE t.geom && $2
               AND ($3 IS NULL OR ST_Within(t.geom, $3))
         ) AS tile
         WHERE tile.mvt_geom IS NOT NULL',
        layer_name,
        schema_name,
        relation_name
    );

    EXECUTE sql_query INTO mvt USING tile_bbox_3857, tile_bbox_4326, filter_geom;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;

GRANT EXECUTE ON FUNCTION gha.clip_to_admin(integer, integer, integer, text, text, text, text) TO PUBLIC;
COMMENT ON FUNCTION gha.clip_to_admin(integer, integer, integer, text, text, text, text)
IS 'Generic tile clipper by admin hierarchy (country/region/district) using ST_Within. table_name must be schema.table';
            """,
            reverse_sql="""
DROP FUNCTION IF EXISTS gha.clip_to_admin(integer, integer, integer, text, text, text, text);
            """,
        ),
    ]
