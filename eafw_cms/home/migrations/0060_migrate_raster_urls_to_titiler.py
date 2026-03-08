# Migration to replace MapServer/MapCache WMS URLs with TiTiler tile URLs
# in geomanager_rastertilelayer.base_url.
#
# The mapviewer reads base_url at runtime and uses it to render tiles.
# TiTiler serves COGs from STAC collections via /cog-tiles/ prefix.

from django.db import migrations

# Known layer identifiers
EXTREME_LAYER_ID = '72ec1db9-dfa8-4cc4-ada5-05af7ac14c41'
TOTAL_RAINFALL_DATASET_ID = 'b8b29e97-e2e5-4c03-861f-0c1061d66bae'

# Old MapServer URLs (from migration 0043)
OLD_EXTREME_URL = (
    '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap'
    '&FORMAT=image/png&TRANSPARENT=true'
    '&LAYERS=wrf_extreme_rainfall&STYLES='
    '&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
    '&percentile={percentile}'
)
OLD_DAILY_URL = (
    '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap'
    '&FORMAT=image/png&TRANSPARENT=true'
    '&LAYERS=wrf_daily_rainfall&STYLES='
    '&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
)

# New TiTiler URLs
NEW_EXTREME_URL = (
    '/cog-tiles/collections/wrf-extreme-rainfall/tiles/'
    'WebMercatorQuad/{z}/{x}/{y}.png?assets=data&percentile={percentile}'
)
NEW_DAILY_URL = (
    '/cog-tiles/collections/wrf-daily-rainfall/tiles/'
    'WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)

# Mapping of known MapServer/MapCache layer names to TiTiler collection IDs
# for any other raster layers that may exist in the DB.
LAYER_COLLECTION_MAP = {
    'flood_extent': 'flood-extent',
    'population': 'population',
    'cropland': 'cropland',
    'rangeland': 'rangeland',
}


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0059_mapscope_site_title_whca_default"),
    ]

    operations = [
        # 1. Update Extreme Rainfall layer (known ID)
        migrations.RunSQL(
            sql=f"""
            UPDATE geomanager_rastertilelayer
            SET base_url = '{NEW_EXTREME_URL}'
            WHERE id = '{EXTREME_LAYER_ID}';
            """,
            reverse_sql=f"""
            UPDATE geomanager_rastertilelayer
            SET base_url = '{OLD_EXTREME_URL}'
            WHERE id = '{EXTREME_LAYER_ID}';
            """,
        ),

        # 2. Update Daily/Total Rainfall layer (find by dataset_id)
        migrations.RunSQL(
            sql=f"""
            UPDATE geomanager_rastertilelayer
            SET base_url = '{NEW_DAILY_URL}'
            WHERE dataset_id = '{TOTAL_RAINFALL_DATASET_ID}';
            """,
            reverse_sql=f"""
            UPDATE geomanager_rastertilelayer
            SET base_url = '{OLD_DAILY_URL}'
            WHERE dataset_id = '{TOTAL_RAINFALL_DATASET_ID}';
            """,
        ),

        # 3. Catch-all: update any remaining layers that still reference
        #    /mapserver/ or /mapcache/ in their base_url.
        #    Extracts the LAYERS= param value from the WMS URL and maps it
        #    to a TiTiler collection endpoint.
        migrations.RunSQL(
            sql="""
            UPDATE geomanager_rastertilelayer
            SET base_url = '/cog-tiles/collections/'
                || REPLACE(
                    SUBSTRING(base_url FROM 'LAYERS=([^&]+)'),
                    '_', '-'
                   )
                || '/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
            WHERE (base_url LIKE '%/mapserver/%' OR base_url LIKE '%/mapcache/%')
              AND base_url LIKE '%LAYERS=%'
              AND id != '""" + EXTREME_LAYER_ID + """'
              AND dataset_id != '""" + TOTAL_RAINFALL_DATASET_ID + """';
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
