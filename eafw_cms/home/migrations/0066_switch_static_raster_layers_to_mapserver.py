from django.db import migrations


FORWARD_SQL = """
    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=flood_extent_rp25&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = '25-year return period';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=flood_extent_rp100&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = '100-year return period';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=asap_cropland&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Crop Land Area Mask';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=asap_rangeland&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Range Land Mask';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=landscan_population&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Landscan Population';
"""


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0065_restore_mapserver_mapcache_raster_urls"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
