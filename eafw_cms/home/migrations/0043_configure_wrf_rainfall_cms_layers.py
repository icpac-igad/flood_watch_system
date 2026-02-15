# Migration to configure the existing "Total Rainfall" and "Extreme Rainfall"
# CMS datasets to use MapServer WMS for WRF rainfall data.
#
# - Updates "Extreme Rainfall" raster tile layer to use MapServer WMS
# - Creates a raster tile layer for "Total Rainfall" dataset
# - Adds legends, timestamps API config, and percentile selector

import uuid
from django.db import migrations

# Dataset IDs (already in the database)
EXTREME_RAINFALL_DATASET_ID = '4f1cfc3b-ba45-43b9-83fb-c7a824969e58'
TOTAL_RAINFALL_DATASET_ID = 'b8b29e97-e2e5-4c03-861f-0c1061d66bae'

# Existing layer ID for extreme rainfall
EXTREME_LAYER_ID = '72ec1db9-dfa8-4cc4-ada5-05af7ac14c41'

# New layer ID for total/daily rainfall
DAILY_LAYER_ID = str(uuid.uuid4())

# MapServer WMS base URLs
DAILY_BASE_URL = (
    '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap'
    '&FORMAT=image/png&TRANSPARENT=true'
    '&LAYERS=wrf_daily_rainfall&STYLES='
    '&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
)

EXTREME_BASE_URL = (
    '/mapserver/?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap'
    '&FORMAT=image/png&TRANSPARENT=true'
    '&LAYERS=wrf_extreme_rainfall&STYLES='
    '&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}'
    '&percentile={percentile}'
)

# Rainfall legend (matching MapServer classification colors)
TOTAL_RAINFALL_LEGEND = (
    '[{"type": "legend", "value": '
    '{"type": "choropleth", "items": ['
    '{"color": "#d9d9d9", "value": "1"},'
    '{"color": "#ffb000", "value": "10"},'
    '{"color": "#fff233", "value": "30"},'
    '{"color": "#9dff58", "value": "50"},'
    '{"color": "#32e646", "value": "100"},'
    '{"color": "#1b9d37", "value": "200 mm"}'
    ']}}]'
)

# Extreme rainfall legend (heavy, very heavy, extremely heavy)
EXTREME_RAINFALL_LEGEND = (
    '[{"type": "legend", "value": '
    '{"type": "basic", "items": ['
    '{"color": "#98dfee", "value": "Heavy Rainfall"},'
    '{"color": "#2b7bd8", "value": "Very Heavy Rainfall"},'
    '{"color": "#091a88", "value": "Extremely Heavy Rainfall"}'
    ']}}]'
)

# Percentile selector for extreme rainfall
PERCENTILE_SELECTOR = (
    '[{"id": "param-percentile", "type": "param", "value": '
    '{"name": "percentile", "label": "Percentile", "type": "radio", '
    '"options": ['
    '{"label": "90th Percentile", "value": "f90", "default": false},'
    '{"label": "95th Percentile", "value": "f95", "default": true},'
    '{"label": "99th Percentile", "value": "f99", "default": false}'
    ']}}]'
)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0042_create_wrf_rainfall_mapserver_functions"),
    ]

    operations = [
        # Update dataset summaries
        migrations.RunSQL(
            sql=f"""
            UPDATE geomanager_dataset
            SET summary = 'WRF model, weekly total rainfall forecast (mm)',
                current_time_method = 'latest_from_source'
            WHERE id = '{TOTAL_RAINFALL_DATASET_ID}';

            UPDATE geomanager_dataset
            SET summary = 'WRF extreme rainfall percentiles (mm)',
                current_time_method = 'latest_from_source'
            WHERE id = '{EXTREME_RAINFALL_DATASET_ID}';
            """,
            reverse_sql=f"""
            UPDATE geomanager_dataset
            SET summary = '', current_time_method = 'latest'
            WHERE id IN ('{TOTAL_RAINFALL_DATASET_ID}', '{EXTREME_RAINFALL_DATASET_ID}');
            """,
        ),

        # Update the existing "Extreme Rainfall" raster tile layer
        migrations.RunSQL(
            sql=f"""
            UPDATE geomanager_rastertilelayer
            SET title = 'Extreme Rainfall',
                base_url = '{EXTREME_BASE_URL}',
                get_time_from_tile_json = true,
                tile_json_url = '/api/v1/wrf/extreme-rainfall/dates',
                timestamps_response_object_key = 'timestamps',
                date_format = 'yyyy-MM-dd',
                time_parameter_name = 'time',
                query_params_selectable = '{PERCENTILE_SELECTOR}'::jsonb,
                legend = '{EXTREME_RAINFALL_LEGEND}'::jsonb
            WHERE id = '{EXTREME_LAYER_ID}';
            """,
            reverse_sql=f"""
            UPDATE geomanager_rastertilelayer
            SET title = 'Extreme Heavy rainfal',
                base_url = 'https://eahazardswatch.icpac.net/mapcache/',
                get_time_from_tile_json = false,
                tile_json_url = NULL,
                date_format = NULL,
                query_params_selectable = '[]'::jsonb,
                legend = '[]'::jsonb
            WHERE id = '{EXTREME_LAYER_ID}';
            """,
        ),

        # Create raster tile layer for "Total Rainfall Forecast" (weekly total)
        migrations.RunSQL(
            sql=f"""
            INSERT INTO geomanager_rastertilelayer (
                id, created, modified, title, "default",
                base_url, get_time_from_tile_json, tile_json_url,
                timestamps_response_object_key, date_format,
                time_parameter_name, dataset_id,
                query_params_static, query_params_selectable,
                params_selectors_side_by_side, legend, more_info, "order"
            ) VALUES (
                '{DAILY_LAYER_ID}', NOW(), NOW(), 'Total Rainfall Forecast', true,
                '{DAILY_BASE_URL}', true, '/api/v1/wrf/daily-rainfall/dates',
                'timestamps', 'yyyy-MM-dd',
                'time', '{TOTAL_RAINFALL_DATASET_ID}',
                '[]'::jsonb, '[]'::jsonb,
                false, '{TOTAL_RAINFALL_LEGEND}'::jsonb, '[]'::jsonb, 0
            );
            """,
            reverse_sql=f"""
            DELETE FROM geomanager_rastertilelayer
            WHERE id = '{DAILY_LAYER_ID}';
            """,
        ),
    ]
