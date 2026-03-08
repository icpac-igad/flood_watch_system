from django.db import migrations


FORWARD_SQL = """
    -- Static rasters: serve via MapCache (cached WMS)
    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=flood_extent_rp25&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = '25-year return period';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=flood_extent_rp100&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = '100-year return period';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=asap_cropland&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Crop Land Area Mask';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=asap_rangeland&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Range Land Mask';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=landscan_population&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Landscan Population';

    -- WRF rasters: serve via MapServer and preserve time discovery from API
    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_daily_rainfall&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}',
           time_parameter_name = 'time'
     WHERE title = 'Total Rainfall Forecast';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_extreme_heavy&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}',
           time_parameter_name = 'time'
     WHERE title = 'Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_extreme_very_heavy&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}',
           time_parameter_name = 'time'
     WHERE title = 'Very Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_extreme_extremely_heavy&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}',
           time_parameter_name = 'time'
     WHERE title = 'Extremely Heavy Rainfall';

    -- Keep DB schema aligned with model definition.
    ALTER TABLE geomanager_rastertilelayer
        ALTER COLUMN base_url TYPE varchar(500);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0064_fix_wrf_titiler_time_defaults"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
