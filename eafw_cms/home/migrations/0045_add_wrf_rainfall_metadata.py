import uuid

from django.db import migrations


EXTREME_RAINFALL_DATASET_ID = uuid.UUID("4f1cfc3b-ba45-43b9-83fb-c7a824969e58")
TOTAL_RAINFALL_DATASET_ID = uuid.UUID("b8b29e97-e2e5-4c03-861f-0c1061d66bae")

EXTREME_RAINFALL_METADATA_ID = uuid.UUID("a3a96f87-a5b5-4fb1-9bd0-603959ef6b25")
TOTAL_RAINFALL_METADATA_ID = uuid.UUID("2769c1e8-97cb-4144-a460-cfca2f97ce3f")


def add_wrf_rainfall_metadata(apps, schema_editor):
    Dataset = apps.get_model("geomanager", "Dataset")
    Metadata = apps.get_model("geomanager", "Metadata")

    Metadata.objects.update_or_create(
        id=TOTAL_RAINFALL_METADATA_ID,
        defaults={
            "title": "WRF Total Rainfall",
            "subtitle": "WRF model weekly total rainfall forecast",
            "function": "Shows forecast weekly accumulated rainfall totals in millimeters.",
            "resolution": "Approximately 0.1 degree grid",
            "geographic_coverage": "Greater Horn of Africa",
            "source": "WRF model output",
            "frequency_of_update": "Daily",
            "overview": (
                "<p>This layer shows model forecast weekly accumulated rainfall totals. "
                "Values are grouped into rainfall intensity classes in millimeters.</p>"
            ),
            "cautions": (
                "<p>WRF rainfall is model guidance and should be interpreted with "
                "other forecast products and local observations.</p>"
            ),
        },
    )

    Metadata.objects.update_or_create(
        id=EXTREME_RAINFALL_METADATA_ID,
        defaults={
            "title": "WRF Extreme Rainfall",
            "subtitle": "WRF percentile rainfall forecast",
            "function": (
                "Shows forecast rainfall intensity percentiles (90th, 95th, 99th) in millimeters."
            ),
            "resolution": "Approximately 0.1 degree grid",
            "geographic_coverage": "Greater Horn of Africa",
            "source": "WRF model output",
            "frequency_of_update": "Daily",
            "overview": (
                "<p>This layer shows extreme rainfall forecast percentiles from the "
                "WRF model output. Use the percentile selector to compare 90th, 95th, "
                "and 99th percentile scenarios.</p>"
            ),
            "cautions": (
                "<p>Higher percentiles represent less frequent but higher impact "
                "scenarios. Use with hydrologic and impact context.</p>"
            ),
        },
    )

    Dataset.objects.filter(id=TOTAL_RAINFALL_DATASET_ID).update(
        metadata_id=TOTAL_RAINFALL_METADATA_ID,
        summary=None,
        current_time_method="latest_from_source",
    )
    Dataset.objects.filter(id=EXTREME_RAINFALL_DATASET_ID).update(
        metadata_id=EXTREME_RAINFALL_METADATA_ID,
        summary=None,
        current_time_method="latest_from_source",
    )


def remove_wrf_rainfall_metadata(apps, schema_editor):
    Dataset = apps.get_model("geomanager", "Dataset")
    Metadata = apps.get_model("geomanager", "Metadata")

    Dataset.objects.filter(id=TOTAL_RAINFALL_DATASET_ID).update(
        metadata_id=None,
        summary="",
        current_time_method="latest",
    )
    Dataset.objects.filter(id=EXTREME_RAINFALL_DATASET_ID).update(
        metadata_id=None,
        summary="",
        current_time_method="latest",
    )

    Metadata.objects.filter(
        id__in=[TOTAL_RAINFALL_METADATA_ID, EXTREME_RAINFALL_METADATA_ID]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0044_remove_extreme_rainfall_summary"),
    ]

    operations = [
        migrations.RunPython(add_wrf_rainfall_metadata, remove_wrf_rainfall_metadata),
    ]
