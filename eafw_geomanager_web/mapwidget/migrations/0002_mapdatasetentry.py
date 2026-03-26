import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mapwidget", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="mapwidgetsettings",
            name="map_datasets",
        ),
        migrations.CreateModel(
            name="MapDatasetEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sort_order",
                    models.IntegerField(blank=True, editable=False, null=True),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Label shown on the toggle button, e.g. 'Drought Risk'",
                        max_length=100,
                        verbose_name="Display Name",
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        blank=True,
                        help_text="Font Awesome class, e.g. 'fas fa-sun' or 'fas fa-cloud-rain'",
                        max_length=150,
                        verbose_name="Icon",
                    ),
                ),
                (
                    "dataset_id",
                    models.CharField(
                        help_text="Select a dataset from the geomanager API",
                        max_length=255,
                        verbose_name="Dataset",
                    ),
                ),
                (
                    "default_active",
                    models.BooleanField(
                        default=False,
                        help_text="Only one dataset can be active by default",
                        verbose_name="Default Active",
                    ),
                ),
                (
                    "settings",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="map_datasets",
                        to="mapwidget.mapwidgetsettings",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
    ]
