from django.db import migrations


FORWARD_SQL = """
    -- Static layers: flood extent return periods
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/flood-extent-return-periods/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = '25-year return period';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/flood-extent-return-periods/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = '100-year return period';

    -- Static layers: land cover masks
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/asap-cropland/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = 'Crop Land Area Mask';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/asap-rangeland/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = 'Range Land Mask';

    -- Static layer: population
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/landscan-population/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = 'Landscan Population';

    -- WRF daily rainfall (time-series, frontend handles search registration)
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-daily-rainfall/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = 'Total Rainfall Forecast';

    -- WRF extreme rainfall: 3 percentile sub-collections
    -- Frontend titiler-style-presets.js matches on -f90/tiles/, -f95/tiles/, -f99/tiles/
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-extreme-rainfall-f90/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = 'Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-extreme-rainfall-f95/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = 'Very Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-extreme-rainfall-f99/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
     WHERE title = 'Extremely Heavy Rainfall';
"""

REVERSE_SQL = """
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

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_daily_rainfall&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Total Rainfall Forecast';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_extreme_heavy&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_extreme_very_heavy&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Very Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/mapcache/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=wrf_extreme_extremely_heavy&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
     WHERE title = 'Extremely Heavy Rainfall';
"""


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0077_fix_multimodal_points_by_admin_source"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
