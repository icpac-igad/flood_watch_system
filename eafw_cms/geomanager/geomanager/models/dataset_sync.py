import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from geomanager.utils.constants import GRID_RESOLUTION_CHOICES, PERIOD_TYPE_CHOICES, DATASET_USE_MODE


class WmsRasterDatasetSync(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name=_("title"), help_text=_("Dataset Sync Manager Title"))
    resolution = models.CharField(
        max_length=255,
        choices=GRID_RESOLUTION_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("resolution"),
        help_text=_("The Spatial resolution of the dataset, for example 10km by 10 km"),
    )
    update_period = models.CharField(
        max_length=100,
        choices=PERIOD_TYPE_CHOICES,
        blank=False,
        null=False,
        verbose_name=_("Dataset Update Period"),
        help_text=_("Frequency of Dataset Update"),
    )
    data_variable = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        verbose_name=_("Data Variable"),
        help_text=_("Raster Dataset Variable/Dimension"),
    )
    filename_pattern = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Dataset filename regex pattern"),
        help_text=_("Regex pattern of dataset file. Guessed by default."),
    )
    dataset_mode = models.CharField(
        max_length=50,
        choices=DATASET_USE_MODE,
        null=False,
        blank=False,
        verbose_name=_("Dataset Mode"),
        help_text=_("Dataset Production and Use Mode"),
    )

    class Meta:
        verbose_name = _("WMS Raster Sync Option")
        verbose_name_plural = _("WMS Raster Sync Options")

    def __str__(self):
        return self.title
