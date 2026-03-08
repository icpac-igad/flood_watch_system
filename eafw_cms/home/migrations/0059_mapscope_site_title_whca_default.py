"""Add site_title field to MapScope and set WHCA as default scope."""

from django.db import migrations, models


def set_whca_default_and_title(apps, schema_editor):
    MapScope = apps.get_model("home", "MapScope")
    # Reset all defaults first
    MapScope.objects.update(is_default=False)
    # Set WHCA as default with site title
    MapScope.objects.filter(key="whca").update(
        is_default=True,
        site_title="Nile Basin Flood Watch",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0058_mapscope"),
    ]

    operations = [
        migrations.AddField(
            model_name="mapscope",
            name="site_title",
            field=models.CharField(
                blank=True,
                help_text="Footer / site title when this scope is active, e.g. 'Nile River Basin Watch'. Leave blank to keep 'East Africa Flood Watch'.",
                max_length=200,
                verbose_name="Site Title Override",
            ),
        ),
        migrations.RunPython(set_whca_default_and_title, migrations.RunPython.noop),
    ]
