from django.db import migrations


FORWARD_SQL = """
-- Fix: resolve_whca_extent_geom was using Nile basin / HydroBASINS geometry
-- as the WHCA clip mask, which cuts off parts of Sudan (Darfur, Kordofan)
-- and Ethiopia (Somali, Afar) that fall outside the watershed.
-- The WHCA project scope should show full country boundaries.
CREATE OR REPLACE FUNCTION gha.resolve_whca_extent_geom()
RETURNS geometry
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    scope_geom geometry;
BEGIN
    -- Always use the union of WHCA member country boundaries.
    -- This ensures full country outlines are shown, not basin-clipped fragments.
    SELECT ST_Multi(ST_MakeValid(ST_UnaryUnion(ST_Collect(geom)))) INTO scope_geom
    FROM gha.admin0
    WHERE country = ANY(gha.get_whca_countries());

    RETURN scope_geom;
END;
$function$;

COMMENT ON FUNCTION gha.resolve_whca_extent_geom()
IS 'Returns the union of WHCA member country geometries as the WHCA extent scope.';
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0068_whca_country_helper_and_admin_fix"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
