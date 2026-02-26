# Migration to convert WMS layers (pointing to MapServer/MapCache) to
# RasterTileLayer entries pointing to TiTiler COG tile endpoints.
#
# Affected layers:
#   - 25-year return period  (flood extent)
#   - 100-year return period (flood extent)
#   - Crop Land Area Mask    (ASAP cropland)
#   - Range Land Mask        (ASAP rangeland)
#   - Landscan Population
#   - GHSL Population        (no local COG yet — disabled)
#
# For each layer we:
#   1. Create a geomanager_rastertilelayer with the TiTiler tile URL
#   2. Update the parent dataset's layer_type from 'wms' to 'raster_tile'
#   3. Delete the WMS request layers (geomanager_wmsrequestlayer)
#   4. Delete the WMS layer (geomanager_wmslayer)

import uuid
from django.db import migrations

# ── WMS layer IDs (from the database) ─────────────────────────────────
WMS_FLOOD_25Y_ID  = 'd71447b3-036c-4237-b438-c58bbddf471c'
WMS_FLOOD_100Y_ID = '4c73e4de-5a8e-4ea7-a940-43bc46f6194d'
WMS_CROPLAND_ID   = '42913e4b-3572-42c3-a21b-f01d569fdac4'
WMS_RANGELAND_ID  = 'fb3ee50f-60ed-43b3-8cb2-28cc28df6d22'
WMS_LANDSCAN_ID   = '75d46390-4d77-455c-9f17-0eb3b39451d1'
WMS_GHSL_ID       = '419e69d3-be47-4acd-ad34-58e00ef2bb34'

# ── Dataset IDs ────────────────────────────────────────────────────────
DS_FLOOD_EXTENT = '1124af5a-f0ee-47d4-94cc-7e3a7e077f3b'
DS_CROPLAND     = 'a3527128-9d22-4668-be3f-b58c60f5c737'
DS_RANGELAND    = '9f2e573c-1b7a-4633-9bd0-d5c85bc412ed'
DS_LANDSCAN     = '0dfaa1b7-a9ed-486d-b214-0c31664fad49'
DS_GHSL         = '14db7336-734d-494b-8287-4e33ac2b2015'

# ── New RasterTileLayer IDs ────────────────────────────────────────────
RTL_FLOOD_25Y_ID  = str(uuid.uuid4())
RTL_FLOOD_100Y_ID = str(uuid.uuid4())
RTL_CROPLAND_ID   = str(uuid.uuid4())
RTL_RANGELAND_ID  = str(uuid.uuid4())
RTL_LANDSCAN_ID   = str(uuid.uuid4())

# ── TiTiler tile URL templates ─────────────────────────────────────────
TITILER_BASE = '/cog-tiles/collections'

FLOOD_25Y_TILE_URL = (
    f'{TITILER_BASE}/flood-extent-return-periods/items/'
    'flood-extent-25y-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)
FLOOD_100Y_TILE_URL = (
    f'{TITILER_BASE}/flood-extent-return-periods/items/'
    'flood-extent-100y-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)
CROPLAND_TILE_URL = (
    f'{TITILER_BASE}/asap-cropland/items/'
    'asap-cropland-1km-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)
RANGELAND_TILE_URL = (
    f'{TITILER_BASE}/asap-rangeland/items/'
    'asap-rangeland-1km-2026/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)
LANDSCAN_TILE_URL = (
    f'{TITILER_BASE}/landscan-population/items/'
    'landscan-population-2024-1km/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data'
)

# ── Legends (copied from existing WMS layers) ─────────────────────────
FLOOD_LEGEND = (
    '[{"type": "legend", "value": '
    '{"type": "basic", "items": ['
    '{"color": "#DEEBF7", "value": "Low consensus (1/6)"},'
    '{"color": "#C6DBEF", "value": "Consensus (2/6)"},'
    '{"color": "#9ECAE1", "value": "Consensus (3/6)"},'
    '{"color": "#6BAED6", "value": "Consensus (4/6)"},'
    '{"color": "#3182BD", "value": "High consensus (5/6)"},'
    '{"color": "#08519C", "value": "Very high consensus (6/6)"}'
    ']}}]'
)

CROPLAND_LEGEND = (
    '[{"type": "legend", "value": '
    '{"type": "basic", "items": ['
    '{"color": "#CFC6C9", "value": "0 to 20 %"},'
    '{"color": "#FFFFCB", "value": "20 to 40%"},'
    '{"color": "#CCE1AC", "value": "40 to 60 %"},'
    '{"color": "#98C38D", "value": "60 to 80%"},'
    '{"color": "#64A46E", "value": "80 to 100 %"}'
    ']}}]'
)

RANGELAND_LEGEND = (
    '[{"type": "legend", "value": '
    '{"type": "basic", "items": ['
    '{"color": "#CFC6C9", "value": "0 to 20 %"},'
    '{"color": "#FFFFCB", "value": "20 to 40 %"},'
    '{"color": "#CCE1AC", "value": "40 to 60 %"},'
    '{"color": "#98C38D", "value": "60 to 80%"},'
    '{"color": "#64A46E", "value": "80 to 100 %"}'
    ']}}]'
)

LANDSCAN_LEGEND = (
    '[{"type": "legend", "value": '
    '{"type": "basic", "items": ['
    '{"color": "#ffffbe", "value": "1 - 5"},'
    '{"color": "#ffff73", "value": "6 - 25"},'
    '{"color": "#ffff00", "value": "26 - 50"},'
    '{"color": "#ffaa00", "value": "51 - 100"},'
    '{"color": "#ff6600", "value": "101 - 500"},'
    '{"color": "#ff0000", "value": "501 - 2500"},'
    '{"color": "#cc0000", "value": "2501 - 5000"},'
    '{"color": "#730000", "value": "5001 and more"}'
    ']}}]'
)

# ── More-info blocks (from existing WMS layers) ───────────────────────
CROPLAND_MORE_INFO = (
    '[{"type": "more_info", "value": '
    '{"text": "A mapping tool that identifies agricultural land, '
    'helping in crop monitoring and food security analysis.", '
    '"link_url": "https://data.jrc.ec.europa.eu/dataset/jrc-10112-10005", '
    '"is_button": true, "link_text": "More Details", "show_arrow": true}}]'
)

RANGELAND_MORE_INFO = (
    '[{"type": "more_info", "value": '
    '{"text": "A dataset identifying grazing land, '
    'supporting livestock management and rangeland conservation.", '
    '"link_url": "https://www.icpac.net/ghacof-57/livestock-and-rangelands-co-production/", '
    '"is_button": true, "link_text": "More Details", "show_arrow": true}}]'
)

LANDSCAN_MORE_INFO = (
    '[{"type": "more_info", "value": '
    '{"text": "The LandScan dataset, provided by the Oak Ridge National Laboratory (ORNL), '
    'offers a comprehensive and high-resolution global population distribution dataset '
    'that serves as a valuable resource for a wide range of applications.", '
    '"link_url": "https://www.eastview.com/resources/e-collections/landscan/", '
    '"is_button": true, "link_text": "More Details", "show_arrow": true}}]'
)


def _insert_raster_tile_layer(layer_id, title, is_default, base_url, dataset_id,
                               legend, more_info, order):
    """Return SQL to insert a raster tile layer."""
    return f"""
        INSERT INTO geomanager_rastertilelayer (
            id, created, modified, title, "default",
            base_url, get_time_from_tile_json, tile_json_url,
            timestamps_response_object_key, date_format,
            time_parameter_name, dataset_id,
            query_params_static, query_params_selectable,
            params_selectors_side_by_side, legend, more_info, "order"
        ) VALUES (
            '{layer_id}', NOW(), NOW(), '{title}', {str(is_default).lower()},
            '{base_url}', false, NULL,
            NULL, NULL,
            NULL, '{dataset_id}',
            '[]'::jsonb, '[]'::jsonb,
            false, '{legend}'::jsonb, '{more_info}'::jsonb, {order}
        );
    """


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0060_migrate_raster_urls_to_titiler"),
    ]

    operations = [
        # ── 1. Create RasterTileLayer entries ──────────────────────────
        migrations.RunSQL(
            sql=(
                _insert_raster_tile_layer(
                    RTL_FLOOD_25Y_ID, '25-year return period', True,
                    FLOOD_25Y_TILE_URL, DS_FLOOD_EXTENT,
                    FLOOD_LEGEND, '[]', 0,
                )
                + _insert_raster_tile_layer(
                    RTL_FLOOD_100Y_ID, '100-year return period', False,
                    FLOOD_100Y_TILE_URL, DS_FLOOD_EXTENT,
                    FLOOD_LEGEND, '[]', 1,
                )
                + _insert_raster_tile_layer(
                    RTL_CROPLAND_ID, 'Crop Land Area Mask', True,
                    CROPLAND_TILE_URL, DS_CROPLAND,
                    CROPLAND_LEGEND, CROPLAND_MORE_INFO, 0,
                )
                + _insert_raster_tile_layer(
                    RTL_RANGELAND_ID, 'Range Land Mask', True,
                    RANGELAND_TILE_URL, DS_RANGELAND,
                    RANGELAND_LEGEND, RANGELAND_MORE_INFO, 0,
                )
                + _insert_raster_tile_layer(
                    RTL_LANDSCAN_ID, 'Landscan Population', True,
                    LANDSCAN_TILE_URL, DS_LANDSCAN,
                    LANDSCAN_LEGEND, LANDSCAN_MORE_INFO, 0,
                )
            ),
            reverse_sql=f"""
                DELETE FROM geomanager_rastertilelayer
                WHERE id IN (
                    '{RTL_FLOOD_25Y_ID}', '{RTL_FLOOD_100Y_ID}',
                    '{RTL_CROPLAND_ID}', '{RTL_RANGELAND_ID}',
                    '{RTL_LANDSCAN_ID}'
                );
            """,
        ),

        # ── 2. Update dataset layer_type from 'wms' to 'raster_tile' ──
        migrations.RunSQL(
            sql=f"""
                UPDATE geomanager_dataset
                SET layer_type = 'raster_tile'
                WHERE id IN (
                    '{DS_FLOOD_EXTENT}', '{DS_CROPLAND}',
                    '{DS_RANGELAND}', '{DS_LANDSCAN}'
                ) AND layer_type = 'wms';
            """,
            reverse_sql=f"""
                UPDATE geomanager_dataset
                SET layer_type = 'wms'
                WHERE id IN (
                    '{DS_FLOOD_EXTENT}', '{DS_CROPLAND}',
                    '{DS_RANGELAND}', '{DS_LANDSCAN}'
                ) AND layer_type = 'raster_tile';
            """,
        ),

        # ── 3. Delete WMS request layers ───────────────────────────────
        migrations.RunSQL(
            sql=f"""
                DELETE FROM geomanager_wmsrequestlayer
                WHERE layer_id IN (
                    '{WMS_FLOOD_25Y_ID}', '{WMS_FLOOD_100Y_ID}',
                    '{WMS_CROPLAND_ID}', '{WMS_RANGELAND_ID}',
                    '{WMS_LANDSCAN_ID}'
                );
            """,
            reverse_sql=f"""
                INSERT INTO geomanager_wmsrequestlayer (name, layer_id)
                VALUES
                    ('flood_extent_rp25', '{WMS_FLOOD_25Y_ID}'),
                    ('flood_extent_rp100', '{WMS_FLOOD_100Y_ID}'),
                    ('asap_cropland', '{WMS_CROPLAND_ID}'),
                    ('asap_rangeland', '{WMS_RANGELAND_ID}'),
                    ('landscan_population_count_tileset', '{WMS_LANDSCAN_ID}');
            """,
        ),

        # ── 4. Delete WMS layers (5 converted + GHSL disabled) ────────
        migrations.RunSQL(
            sql=f"""
                DELETE FROM geomanager_wmslayer
                WHERE id IN (
                    '{WMS_FLOOD_25Y_ID}', '{WMS_FLOOD_100Y_ID}',
                    '{WMS_CROPLAND_ID}', '{WMS_RANGELAND_ID}',
                    '{WMS_LANDSCAN_ID}', '{WMS_GHSL_ID}'
                );
            """,
            reverse_sql=f"""
                INSERT INTO geomanager_wmslayer (
                    id, created, modified, title, "default", base_url,
                    dataset_id, legend, more_info, can_clip, "order",
                    version, width, height, transparent, srs, format,
                    wms_query_params_selectable, params_selectors_side_by_side,
                    request_time_from_capabilities
                ) VALUES
                ('{WMS_FLOOD_25Y_ID}', NOW(), NOW(), '25-year return period', true,
                 '/mapcache/', '{DS_FLOOD_EXTENT}',
                 '{FLOOD_LEGEND}'::jsonb, '[]'::jsonb, false, 0,
                 '1.1.1', 256, 256, true, 'EPSG:3857', 'image/png',
                 '[]'::jsonb, false, false),
                ('{WMS_FLOOD_100Y_ID}', NOW(), NOW(), '100-year return period', false,
                 '/mapcache/', '{DS_FLOOD_EXTENT}',
                 '{FLOOD_LEGEND}'::jsonb, '[]'::jsonb, false, 1,
                 '1.1.1', 256, 256, true, 'EPSG:3857', 'image/png',
                 '[]'::jsonb, false, false),
                ('{WMS_CROPLAND_ID}', NOW(), NOW(), 'Crop Land Area Mask', true,
                 '/mapcache/', '{DS_CROPLAND}',
                 '{CROPLAND_LEGEND}'::jsonb, '{CROPLAND_MORE_INFO}'::jsonb, false, 0,
                 '1.1.1', 256, 256, true, 'EPSG:3857', 'image/png',
                 '[]'::jsonb, false, false),
                ('{WMS_RANGELAND_ID}', NOW(), NOW(), 'Range Land Mask', true,
                 '/mapcache/', '{DS_RANGELAND}',
                 '{RANGELAND_LEGEND}'::jsonb, '{RANGELAND_MORE_INFO}'::jsonb, false, 0,
                 '1.1.1', 256, 256, true, 'EPSG:3857', 'image/png',
                 '[]'::jsonb, false, false),
                ('{WMS_LANDSCAN_ID}', NOW(), NOW(), 'Landscan Population Pojections', true,
                 'https://eahazardswatch.icpac.net/mapcache/', '{DS_LANDSCAN}',
                 '{LANDSCAN_LEGEND}'::jsonb, '{LANDSCAN_MORE_INFO}'::jsonb, false, 0,
                 '1.1.1', 256, 256, true, 'EPSG:3857', 'image/png',
                 '[]'::jsonb, false, false),
                ('{WMS_GHSL_ID}', NOW(), NOW(), 'GHSL Population Pojections', true,
                 'https://eahazardswatch.icpac.net/mapcache/', '{DS_GHSL}',
                 '[]'::jsonb, '[]'::jsonb, false, 0,
                 '1.1.1', 256, 256, true, 'EPSG:3857', 'image/png',
                 '[]'::jsonb, false, false);
            """,
        ),

        # ── 5. Delete GHSL request layer ───────────────────────────────
        migrations.RunSQL(
            sql=f"""
                DELETE FROM geomanager_wmsrequestlayer
                WHERE layer_id = '{WMS_GHSL_ID}';
            """,
            reverse_sql=f"""
                INSERT INTO geomanager_wmsrequestlayer (name, layer_id)
                VALUES ('ghsl_population_count_tileset', '{WMS_GHSL_ID}');
            """,
        ),
    ]
