from django.db import migrations


EXTREME_RAINFALL_DATASET_ID = "4f1cfc3b-ba45-43b9-83fb-c7a824969e58"
PREVIOUS_SUMMARY = "WRF extreme rainfall percentiles (mm)"


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0043_configure_wrf_rainfall_cms_layers"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"""
            UPDATE geomanager_dataset
            SET summary = NULL
            WHERE id = '{EXTREME_RAINFALL_DATASET_ID}';
            """,
            reverse_sql=f"""
            UPDATE geomanager_dataset
            SET summary = '{PREVIOUS_SUMMARY}'
            WHERE id = '{EXTREME_RAINFALL_DATASET_ID}';
            """,
        ),
    ]
