from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0073_fix_geometry_collections_and_performance"),
    ]

    operations = [
        migrations.AddField(
            model_name="mapcategory",
            name="fa_icon_class",
            field=models.CharField(
                blank=True,
                help_text="Optional Font Awesome classes, e.g. 'fa-solid fa-cloud-rain'",
                max_length=120,
                verbose_name="Font Awesome Class",
            ),
        ),
    ]
