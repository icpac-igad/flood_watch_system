from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.models import Orderable

from wagtailiconchooser.widgets import IconChooserWidget

from .widgets import DatasetChooserWidget


class MapDatasetEntry(Orderable):
    """One toggle-able dataset entry in the map widget."""

    settings = ParentalKey(
        "MapWidgetSettings",
        on_delete=models.CASCADE,
        related_name="map_datasets",
    )
    title = models.CharField(
        max_length=100,
        verbose_name=_("Display Name"),
        help_text=_("Label shown on the toggle button, e.g. 'Drought Risk'"),
    )
    icon = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Icon"),
        help_text=_("Pick an icon for this dataset toggle button"),
    )
    dataset_id = models.CharField(
        max_length=255,
        verbose_name=_("Dataset"),
        help_text=_("Select a dataset from the geomanager API"),
    )
    default_active = models.BooleanField(
        default=False,
        verbose_name=_("Default Active"),
        help_text=_("Only one dataset can be active by default"),
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("icon", widget=IconChooserWidget),
        FieldPanel("dataset_id", widget=DatasetChooserWidget),
        FieldPanel("default_active"),
    ]

    def __str__(self):
        return self.title


@register_setting(icon="map")
class MapWidgetSettings(BaseGenericSetting, ClusterableModel):
    show_map_widget = models.BooleanField(
        default=False,
        verbose_name=_("Show Map Widget"),
        help_text=_("Display the interactive map section on the homepage"),
    )
    map_widget_heading = models.CharField(
        max_length=200,
        blank=True,
        default="Explore Our Data",
        verbose_name=_("Map Widget Heading"),
    )
    boundary_dataset_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Boundary Dataset"),
        help_text=_("Select the admin boundary dataset to display on the map"),
    )
    map_logo = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Map Logo"),
        help_text=_("Logo image displayed at the bottom-left of the map"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    map_cta_text = models.CharField(
        max_length=200,
        blank=True,
        default="For more risk information",
        verbose_name=_("CTA Text"),
        help_text=_("Descriptive text shown to the left of the action buttons below the map"),
    )
    map_cta_button_label = models.CharField(
        max_length=100,
        blank=True,
        default="Explore on Hazards Watch",
        verbose_name=_("CTA Button 1 Label"),
        help_text=_("Text for the first action button"),
    )
    map_cta_button_url = models.CharField(
        max_length=500,
        blank=True,
        default="/mapviewer",
        verbose_name=_("CTA Button 1 URL"),
        help_text=_("Link for the first action button (e.g. /mapviewer or https://example.com)"),
    )
    map_cta_button_label_2 = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("CTA Button 2 Label"),
        help_text=_("Text for the second action button (leave blank to hide)"),
    )
    map_cta_button_url_2 = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("CTA Button 2 URL"),
        help_text=_("Link for the second action button (e.g. /mapviewer or https://example.com)"),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("show_map_widget"),
                FieldPanel("map_widget_heading"),
                FieldPanel("map_logo"),
            ],
            heading=_("Map Widget"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("boundary_dataset_id", widget=DatasetChooserWidget),
            ],
            heading=_("Admin Boundary"),
        ),
        InlinePanel("map_datasets", heading=_("Map Datasets"), label=_("Dataset"), max_num=4),
        MultiFieldPanel(
            [
                FieldPanel("map_cta_text"),
                FieldPanel("map_cta_button_label"),
                FieldPanel("map_cta_button_url"),
                FieldPanel("map_cta_button_label_2"),
                FieldPanel("map_cta_button_url_2"),
            ],
            heading=_("Call to Action"),
        ),
    ]

    class Meta:
        verbose_name = _("Homepage Map Widget")
        verbose_name_plural = _("Homepage Map Widget")

    def save(self, *args, **kwargs):
        """Enforce a single default_active entry across all dataset entries."""
        super().save(*args, **kwargs)
        defaults = self.map_datasets.filter(default_active=True)
        if defaults.count() > 1:
            keep = defaults.last()
            defaults.exclude(pk=keep.pk).update(default_active=False)
