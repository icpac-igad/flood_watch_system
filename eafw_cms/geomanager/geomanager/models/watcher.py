import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from wagtail.admin.panels import FieldPanel, MultiFieldPanel

from geomanager.utils.constants import (
    DATE_FORMAT_CHOICES,
    PARSER_TYPE_CHOICES,
    PERIOD_TYPE_CHOICES,
)


class WatcherConfig(TimeStampedModel):
    """
    Reusable watcher configuration for automated dataset updates.

    This model stores the configuration for fetching and parsing dates from external APIs.
    Multiple datasets can share the same WatcherConfig instance.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=255,
        verbose_name=_("Configuration Name"),
        help_text=_("Name for this watcher configuration (e.g., 'ICPAC Dekadal CDI API')"),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Optional description of what this watcher configuration does"),
    )

    # API Configuration
    api_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("API URL"),
        help_text=_("URL to fetch the latest date from"),
    )

    auto_update_frequency = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Update Frequency (minutes)"),
        help_text=_("How often to check for updates (in minutes)"),
    )

    # Parser Configuration
    parser_type = models.CharField(
        max_length=50,
        choices=PARSER_TYPE_CHOICES,
        default="direct_date_field",
        verbose_name=_("Date Parser Type"),
        help_text=_("How to extract the date from the API response"),
    )

    # For direct_date_field parser
    json_path = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Date Field Path"),
        help_text=_(
            "Path to date field using dot or array notation (e.g. 'last_updated', "
            "'features[0].properties.date', or 'data.properties.date')"
        ),
    )

    date_format = models.CharField(
        max_length=100,
        choices=DATE_FORMAT_CHOICES,
        blank=True,
        null=True,
        default="yyyy-MM-dd",
        verbose_name=_("Expected Date Format from API"),
        help_text=_("The format of the date value returned by the API. Used only for direct_date_field parser type."),
    )

    # For multi_field_constructor parser
    year_field = models.CharField(
        max_length=100,
        blank=True,
        default="end_year",
        verbose_name=_("Year Field Name"),
        help_text=_("Name of the field containing the year value"),
    )

    month_field = models.CharField(
        max_length=100,
        blank=True,
        default="end_month",
        verbose_name=_("Month Field Name"),
        help_text=_("Name of the field containing the month value"),
    )

    day_field = models.CharField(
        max_length=100,
        blank=True,
        default="end_dekad",
        verbose_name=_("Day Field Name"),
        help_text=_("Name of the field containing the day value"),
    )

    # Period Configuration
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default="dekadal",
        verbose_name=_("Period Type"),
        help_text=_("Type of periodic dates for this dataset (affects date generation and backfilling)"),
    )

    dataset_start_year = models.IntegerField(
        default=2000,
        verbose_name=_("Start Year"),
        help_text=_("Start year for generating historical dates"),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
                FieldPanel("description"),
            ],
            heading=_("Basic Information"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("api_url"),
                FieldPanel("auto_update_frequency"),
            ],
            heading=_("API Configuration"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("parser_type"),
                FieldPanel("json_path"),
                FieldPanel("date_format"),
                FieldPanel("year_field"),
                FieldPanel("month_field"),
                FieldPanel("day_field"),
            ],
            heading=_("Parser Configuration"),
            classname="parser-config",
        ),
        MultiFieldPanel(
            [
                FieldPanel("period_type"),
                FieldPanel("dataset_start_year"),
            ],
            heading=_("Period Configuration"),
        ),
    ]

    class Meta:
        verbose_name = _("Watcher Configuration")
        verbose_name_plural = _("Watcher Configurations")
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_parser_config(self):
        """Convert model fields to parser config dictionary for use in watcher tasks."""
        if self.parser_type == "direct_date_field":
            config = {"json_path": self.json_path}
            if self.date_format:
                config["date_format"] = self.date_format
            return config

        elif self.parser_type == "multi_field_constructor":
            return {
                "template": "{year}-{month:02d}-{day}",
                "field_mappings": {
                    "year": self.year_field,
                    "month": self.month_field,
                    "day": self.day_field,
                },
            }

        return {}
