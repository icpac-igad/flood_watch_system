"""Rename WHCA scope titles from 'Flood' to 'Hydromet'."""

from django.db import migrations


def rename_whca_titles(apps, schema_editor):
    MapScope = apps.get_model("home", "MapScope")
    MapScope.objects.filter(key="whca").update(
        site_title="Nile Basin Hydromet Watch",
        country_section_title="Nile Basin Hydromet Situation",
        dashboard_title="Latest Situation of Nile Basin Hydromet Conditions",
    )


def revert_whca_titles(apps, schema_editor):
    MapScope = apps.get_model("home", "MapScope")
    MapScope.objects.filter(key="whca").update(
        site_title="Nile Basin Flood Watch",
        country_section_title="Nile Basin Flood Situation",
        dashboard_title="Latest Situation of Nile Basin Flood Conditions",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0066_switch_static_raster_layers_to_mapserver"),
    ]

    operations = [
        migrations.RunPython(rename_whca_titles, revert_whca_titles),
    ]
