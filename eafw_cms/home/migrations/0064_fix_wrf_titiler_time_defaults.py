from django.db import migrations


TOTAL_RAINFALL_DATASET_ID = "b8b29e97-e2e5-4c03-861f-0c1061d66bae"
EXTREME_RAINFALL_DATASET_ID = "4f1cfc3b-ba45-43b9-83fb-c7a824969e58"


FORWARD_SQL = f"""
    -- Open WRF layers on the most recent date <= now instead of farthest forecast date.
    UPDATE geomanager_dataset
       SET current_time_method = 'previous_to_now'
     WHERE id IN ('{TOTAL_RAINFALL_DATASET_ID}', '{EXTREME_RAINFALL_DATASET_ID}');

    -- TiTiler collection endpoints use `datetime` for temporal filtering.
    UPDATE geomanager_rastertilelayer
       SET time_parameter_name = 'datetime'
     WHERE get_time_from_tile_json = true
       AND dataset_id IN ('{TOTAL_RAINFALL_DATASET_ID}', '{EXTREME_RAINFALL_DATASET_ID}');
"""


REVERSE_SQL = f"""
    UPDATE geomanager_dataset
       SET current_time_method = 'latest_from_source'
     WHERE id IN ('{TOTAL_RAINFALL_DATASET_ID}', '{EXTREME_RAINFALL_DATASET_ID}');

    UPDATE geomanager_rastertilelayer
       SET time_parameter_name = 'time'
     WHERE get_time_from_tile_json = true
       AND dataset_id IN ('{TOTAL_RAINFALL_DATASET_ID}', '{EXTREME_RAINFALL_DATASET_ID}');
"""


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0063_fix_titiler_item_ids_and_wrf_styles"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
