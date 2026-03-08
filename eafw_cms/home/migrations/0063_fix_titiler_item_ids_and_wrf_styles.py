from django.db import migrations


# Mapfile-aligned color ramps (URL-encoded JSON colormaps)
WRF_TOTAL_COLORMAP = (
    "%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C"
    "%221%22%3A%5B217%2C217%2C217%2C255%5D%2C"
    "%2210%22%3A%5B217%2C217%2C217%2C255%5D%2C"
    "%2211%22%3A%5B255%2C176%2C0%2C255%5D%2C"
    "%2230%22%3A%5B255%2C176%2C0%2C255%5D%2C"
    "%2231%22%3A%5B255%2C242%2C51%2C255%5D%2C"
    "%2250%22%3A%5B255%2C242%2C51%2C255%5D%2C"
    "%2251%22%3A%5B157%2C255%2C88%2C255%5D%2C"
    "%22100%22%3A%5B157%2C255%2C88%2C255%5D%2C"
    "%22101%22%3A%5B50%2C230%2C70%2C255%5D%2C"
    "%22200%22%3A%5B50%2C230%2C70%2C255%5D%2C"
    "%22201%22%3A%5B27%2C157%2C55%2C255%5D%2C"
    "%222000%22%3A%5B27%2C157%2C55%2C255%5D%7D"
)

WRF_HEAVY_COLORMAP = (
    "%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C"
    "%221%22%3A%5B152%2C223%2C238%2C255%5D%2C"
    "%22255%22%3A%5B152%2C223%2C238%2C255%5D%7D"
)

WRF_VERY_HEAVY_COLORMAP = (
    "%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C"
    "%221%22%3A%5B43%2C123%2C216%2C255%5D%2C"
    "%22255%22%3A%5B43%2C123%2C216%2C255%5D%7D"
)

WRF_EXTREME_COLORMAP = (
    "%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C"
    "%221%22%3A%5B9%2C26%2C136%2C255%5D%2C"
    "%22255%22%3A%5B9%2C26%2C136%2C255%5D%7D"
)


FORWARD_SQL = f"""
    -- Use discovered STAC item IDs (existing IDs from old migrations are stale for some layers)
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/flood-extent-return-periods/items/M6_25y_clipped/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=nearest&colormap=%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C%221%22%3A%5B222%2C235%2C247%2C255%5D%2C%222%22%3A%5B198%2C219%2C239%2C255%5D%2C%223%22%3A%5B158%2C202%2C225%2C255%5D%2C%224%22%3A%5B107%2C174%2C214%2C255%5D%2C%225%22%3A%5B49%2C130%2C189%2C255%5D%2C%226%22%3A%5B8%2C81%2C156%2C255%5D%7D'
     WHERE title = '25-year return period';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/flood-extent-return-periods/items/M6_100y_clipped/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=nearest&colormap=%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C%221%22%3A%5B222%2C235%2C247%2C255%5D%2C%222%22%3A%5B198%2C219%2C239%2C255%5D%2C%223%22%3A%5B158%2C202%2C225%2C255%5D%2C%224%22%3A%5B107%2C174%2C214%2C255%5D%2C%225%22%3A%5B49%2C130%2C189%2C255%5D%2C%226%22%3A%5B8%2C81%2C156%2C255%5D%7D'
     WHERE title = '100-year return period';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/asap-cropland/items/asap_cropland_gha/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=nearest&colormap=%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C%221%22%3A%5B207%2C198%2C201%2C255%5D%2C%2220%22%3A%5B207%2C198%2C201%2C255%5D%2C%2221%22%3A%5B255%2C255%2C203%2C255%5D%2C%2240%22%3A%5B255%2C255%2C203%2C255%5D%2C%2241%22%3A%5B204%2C225%2C172%2C255%5D%2C%2280%22%3A%5B204%2C225%2C172%2C255%5D%2C%2281%22%3A%5B152%2C195%2C141%2C255%5D%2C%22120%22%3A%5B152%2C195%2C141%2C255%5D%2C%22121%22%3A%5B100%2C164%2C110%2C255%5D%2C%22160%22%3A%5B100%2C164%2C110%2C255%5D%2C%22161%22%3A%5B48%2C134%2C80%2C255%5D%2C%22255%22%3A%5B48%2C134%2C80%2C255%5D%7D'
     WHERE title = 'Crop Land Area Mask';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/asap-rangeland/items/asap_rangeland_gha/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=nearest&colormap=%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C%221%22%3A%5B207%2C198%2C201%2C255%5D%2C%2220%22%3A%5B207%2C198%2C201%2C255%5D%2C%2221%22%3A%5B255%2C255%2C203%2C255%5D%2C%2240%22%3A%5B255%2C255%2C203%2C255%5D%2C%2241%22%3A%5B204%2C225%2C172%2C255%5D%2C%2280%22%3A%5B204%2C225%2C172%2C255%5D%2C%2281%22%3A%5B152%2C195%2C141%2C255%5D%2C%22120%22%3A%5B152%2C195%2C141%2C255%5D%2C%22121%22%3A%5B100%2C164%2C110%2C255%5D%2C%22160%22%3A%5B100%2C164%2C110%2C255%5D%2C%22161%22%3A%5B48%2C134%2C80%2C255%5D%2C%22255%22%3A%5B48%2C134%2C80%2C255%5D%7D'
     WHERE title = 'Range Land Mask';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/landscan-population/items/landscan_population_2024/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=bilinear&colormap=%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C%221%22%3A%5B255%2C255%2C190%2C255%5D%2C%225%22%3A%5B255%2C255%2C190%2C255%5D%2C%226%22%3A%5B255%2C255%2C115%2C255%5D%2C%2225%22%3A%5B255%2C255%2C115%2C255%5D%2C%2226%22%3A%5B255%2C255%2C0%2C255%5D%2C%2250%22%3A%5B255%2C255%2C0%2C255%5D%2C%2251%22%3A%5B255%2C170%2C0%2C255%5D%2C%22100%22%3A%5B255%2C170%2C0%2C255%5D%2C%22101%22%3A%5B255%2C102%2C0%2C255%5D%2C%22500%22%3A%5B255%2C102%2C0%2C255%5D%2C%22501%22%3A%5B255%2C0%2C0%2C255%5D%2C%222500%22%3A%5B255%2C0%2C0%2C255%5D%2C%222501%22%3A%5B204%2C0%2C0%2C255%5D%2C%225000%22%3A%5B204%2C0%2C0%2C255%5D%2C%225001%22%3A%5B115%2C0%2C0%2C255%5D%2C%2265535%22%3A%5B115%2C0%2C0%2C255%5D%7D'
     WHERE title = 'Landscan Population';

    -- Total rainfall: mapfile-aligned ramp + rescale
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-daily-rainfall/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=bilinear&rescale=0%2C200&colormap={WRF_TOTAL_COLORMAP}'
     WHERE title = 'Total Rainfall Forecast';

    -- Extreme rainfall classes served from one operational extreme collection.
    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-extreme-rainfall/items/wrf-extreme-{{time}}-f90/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=nearest&rescale=0%2C1&colormap={WRF_HEAVY_COLORMAP}'
     WHERE title = 'Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-extreme-rainfall/items/wrf-extreme-{{time}}-f95/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=nearest&rescale=0%2C1&colormap={WRF_VERY_HEAVY_COLORMAP}'
     WHERE title = 'Very Heavy Rainfall';

    UPDATE geomanager_rastertilelayer
       SET base_url = '/cog-tiles/collections/wrf-extreme-rainfall/items/wrf-extreme-{{time}}-f99/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png?assets=data&resampling=nearest&rescale=0%2C1&colormap={WRF_EXTREME_COLORMAP}'
     WHERE title = 'Extremely Heavy Rainfall';
"""


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0062_add_colormaps_to_raster_tile_urls"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
