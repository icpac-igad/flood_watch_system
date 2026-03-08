# Migration to add colormap and resampling query parameters to RasterTileLayer
# base_url columns.  The previous migration (0061) created the layers with
# bare "?assets=data" URLs.  TiTiler requires an explicit colormap for
# correct rendering — without it the tiles come back as single-band grey.
#
# This migration also widens the base_url column from varchar(500) to
# varchar(2000) because the URL-encoded colormap JSON makes the URLs longer
# than 500 characters.

from django.db import migrations

# ── URL-encoded colormaps (extracted from STAC item preview links) ────────

# Flood extent 25y / 100y  (blues, 7 classes including nodata-transparent)
FLOOD_COLORMAP = (
    '%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C'
    '%221%22%3A%5B222%2C235%2C247%2C255%5D%2C'
    '%222%22%3A%5B198%2C219%2C239%2C255%5D%2C'
    '%223%22%3A%5B158%2C202%2C225%2C255%5D%2C'
    '%224%22%3A%5B107%2C174%2C214%2C255%5D%2C'
    '%225%22%3A%5B49%2C130%2C189%2C255%5D%2C'
    '%226%22%3A%5B8%2C81%2C156%2C255%5D%7D'
)

# ASAP cropland / rangeland  (grey-to-green, 13 classes including nodata)
LANDCOVER_COLORMAP = (
    '%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C'
    '%221%22%3A%5B207%2C198%2C201%2C255%5D%2C'
    '%2220%22%3A%5B207%2C198%2C201%2C255%5D%2C'
    '%2221%22%3A%5B255%2C255%2C203%2C255%5D%2C'
    '%2240%22%3A%5B255%2C255%2C203%2C255%5D%2C'
    '%2241%22%3A%5B204%2C225%2C172%2C255%5D%2C'
    '%2280%22%3A%5B204%2C225%2C172%2C255%5D%2C'
    '%2281%22%3A%5B152%2C195%2C141%2C255%5D%2C'
    '%22120%22%3A%5B152%2C195%2C141%2C255%5D%2C'
    '%22121%22%3A%5B100%2C164%2C110%2C255%5D%2C'
    '%22160%22%3A%5B100%2C164%2C110%2C255%5D%2C'
    '%22161%22%3A%5B48%2C134%2C80%2C255%5D%2C'
    '%22255%22%3A%5B48%2C134%2C80%2C255%5D%7D'
)

# LandScan population  (yellow-to-dark-red, 17 classes including nodata)
POPULATION_COLORMAP = (
    '%7B%220%22%3A%5B0%2C0%2C0%2C0%5D%2C'
    '%221%22%3A%5B255%2C255%2C190%2C255%5D%2C'
    '%225%22%3A%5B255%2C255%2C190%2C255%5D%2C'
    '%226%22%3A%5B255%2C255%2C115%2C255%5D%2C'
    '%2225%22%3A%5B255%2C255%2C115%2C255%5D%2C'
    '%2226%22%3A%5B255%2C255%2C0%2C255%5D%2C'
    '%2250%22%3A%5B255%2C255%2C0%2C255%5D%2C'
    '%2251%22%3A%5B255%2C170%2C0%2C255%5D%2C'
    '%22100%22%3A%5B255%2C170%2C0%2C255%5D%2C'
    '%22101%22%3A%5B255%2C102%2C0%2C255%5D%2C'
    '%22500%22%3A%5B255%2C102%2C0%2C255%5D%2C'
    '%22501%22%3A%5B255%2C0%2C0%2C255%5D%2C'
    '%222500%22%3A%5B255%2C0%2C0%2C255%5D%2C'
    '%222501%22%3A%5B204%2C0%2C0%2C255%5D%2C'
    '%225000%22%3A%5B204%2C0%2C0%2C255%5D%2C'
    '%225001%22%3A%5B115%2C0%2C0%2C255%5D%2C'
    '%2265535%22%3A%5B115%2C0%2C0%2C255%5D%7D'
)

# ── TiTiler tile URL base ────────────────────────────────────────────────
TITILER_BASE = '/cog-tiles/collections'

# ── New full URLs (with colormap + resampling) ───────────────────────────
FLOOD_25Y_URL_NEW = (
    f'{TITILER_BASE}/flood-extent-return-periods/items/'
    f'flood-extent-25y-2026/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png'
    f'?assets=data&resampling=nearest&colormap={FLOOD_COLORMAP}'
)

FLOOD_100Y_URL_NEW = (
    f'{TITILER_BASE}/flood-extent-return-periods/items/'
    f'flood-extent-100y-2026/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png'
    f'?assets=data&resampling=nearest&colormap={FLOOD_COLORMAP}'
)

CROPLAND_URL_NEW = (
    f'{TITILER_BASE}/asap-cropland/items/'
    f'asap-cropland-1km-2026/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png'
    f'?assets=data&resampling=nearest&colormap={LANDCOVER_COLORMAP}'
)

RANGELAND_URL_NEW = (
    f'{TITILER_BASE}/asap-rangeland/items/'
    f'asap-rangeland-1km-2026/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png'
    f'?assets=data&resampling=nearest&colormap={LANDCOVER_COLORMAP}'
)

LANDSCAN_URL_NEW = (
    f'{TITILER_BASE}/landscan-population/items/'
    f'landscan-population-2024-1km/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png'
    f'?assets=data&resampling=bilinear&colormap={POPULATION_COLORMAP}'
)

# ── Old URLs (bare ?assets=data, from migration 0061) ────────────────────
FLOOD_25Y_URL_OLD = (
    f'{TITILER_BASE}/flood-extent-return-periods/items/'
    'flood-extent-25y-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)

FLOOD_100Y_URL_OLD = (
    f'{TITILER_BASE}/flood-extent-return-periods/items/'
    'flood-extent-100y-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)

CROPLAND_URL_OLD = (
    f'{TITILER_BASE}/asap-cropland/items/'
    'asap-cropland-1km-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)

RANGELAND_URL_OLD = (
    f'{TITILER_BASE}/asap-rangeland/items/'
    'asap-rangeland-1km-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)

LANDSCAN_URL_OLD = (
    f'{TITILER_BASE}/landscan-population/items/'
    'landscan-population-2024-1km/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)


# ── SQL helpers ──────────────────────────────────────────────────────────

FORWARD_SQL = f"""
    -- Widen base_url to accommodate colormap query strings
    ALTER TABLE geomanager_rastertilelayer
        ALTER COLUMN base_url TYPE varchar(2000);

    -- 25-year return period
    UPDATE geomanager_rastertilelayer
       SET base_url = '{FLOOD_25Y_URL_NEW}'
     WHERE title = '25-year return period'
       AND base_url LIKE '%flood-extent-25y-2026%';

    -- 100-year return period
    UPDATE geomanager_rastertilelayer
       SET base_url = '{FLOOD_100Y_URL_NEW}'
     WHERE title = '100-year return period'
       AND base_url LIKE '%flood-extent-100y-2026%';

    -- Crop Land Area Mask
    UPDATE geomanager_rastertilelayer
       SET base_url = '{CROPLAND_URL_NEW}'
     WHERE title = 'Crop Land Area Mask'
       AND base_url LIKE '%asap-cropland-1km-2026%';

    -- Range Land Mask
    UPDATE geomanager_rastertilelayer
       SET base_url = '{RANGELAND_URL_NEW}'
     WHERE title = 'Range Land Mask'
       AND base_url LIKE '%asap-rangeland-1km-2026%';

    -- Landscan Population
    UPDATE geomanager_rastertilelayer
       SET base_url = '{LANDSCAN_URL_NEW}'
     WHERE title = 'Landscan Population'
       AND base_url LIKE '%landscan-population-2024-1km%';
"""

REVERSE_SQL = f"""
    -- Revert URLs to bare ?assets=data (strip colormap + resampling)
    UPDATE geomanager_rastertilelayer
       SET base_url = '{FLOOD_25Y_URL_OLD}'
     WHERE title = '25-year return period'
       AND base_url LIKE '%flood-extent-25y-2026%';

    UPDATE geomanager_rastertilelayer
       SET base_url = '{FLOOD_100Y_URL_OLD}'
     WHERE title = '100-year return period'
       AND base_url LIKE '%flood-extent-100y-2026%';

    UPDATE geomanager_rastertilelayer
       SET base_url = '{CROPLAND_URL_OLD}'
     WHERE title = 'Crop Land Area Mask'
       AND base_url LIKE '%asap-cropland-1km-2026%';

    UPDATE geomanager_rastertilelayer
       SET base_url = '{RANGELAND_URL_OLD}'
     WHERE title = 'Range Land Mask'
       AND base_url LIKE '%asap-rangeland-1km-2026%';

    UPDATE geomanager_rastertilelayer
       SET base_url = '{LANDSCAN_URL_OLD}'
     WHERE title = 'Landscan Population'
       AND base_url LIKE '%landscan-population-2024-1km%';

    -- Shrink base_url back to original size
    ALTER TABLE geomanager_rastertilelayer
        ALTER COLUMN base_url TYPE varchar(500);
"""


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0061_convert_wms_layers_to_raster_tile"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
