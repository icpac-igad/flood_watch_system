from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.api import APIField
from wagtail.search import index

from .blocks import ChapterBlock, CountryEventBlock


class StorylineIndexPage(Page):
    """Landing page that lists all published storylines."""

    max_count = 1
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["storylines.StorylinePage"]

    intro = RichTextField(
        blank=True,
        features=["bold", "italic", "link"],
        verbose_name=_("Introduction"),
        help_text=_("Optional intro text shown above the storylines list"),
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    class Meta:
        verbose_name = _("Storyline Index")

    def get_storylines(self):
        return StorylinePage.objects.live().descendant_of(self).order_by("-event_start")


class StorylinePage(Page):
    """A single flood event storyline with scrollytelling chapters."""

    parent_page_types = ["storylines.StorylineIndexPage"]
    subpage_types = []

    description = models.TextField(
        verbose_name=_("Short Description"),
        help_text=_("Brief summary shown on story cards (1-2 sentences)"),
    )
    cover_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Cover Image"),
    )
    event_start = models.DateField(
        verbose_name=_("Event Start Date"),
        help_text=_("When the flood event began"),
    )
    event_end = models.DateField(
        verbose_name=_("Event End Date"),
        help_text=_("When the flood event ended"),
    )
    region = models.CharField(
        max_length=100,
        default="East Africa",
        verbose_name=_("Region"),
        help_text=_("Geographic region (e.g., 'East Africa', 'Horn of Africa')"),
    )
    total_affected = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Total People Affected"),
    )
    total_displaced = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Total People Displaced"),
    )
    total_deaths = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Total Deaths"),
    )

    # Country events table
    country_events = StreamField(
        [("event", CountryEventBlock())],
        blank=True,
        verbose_name=_("Country Events"),
        help_text=_("Countries affected and their EM-DAT codes"),
    )

    # Scrollytelling chapters
    chapters = StreamField(
        [("chapter", ChapterBlock())],
        verbose_name=_("Story Chapters"),
        help_text=_("The narrative chapters that drive the scrollytelling experience"),
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("description"),
                FieldPanel("cover_image"),
                FieldPanel("region"),
            ],
            heading=_("Story Overview"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("event_start"),
                FieldPanel("event_end"),
                FieldPanel("total_affected"),
                FieldPanel("total_displaced"),
                FieldPanel("total_deaths"),
            ],
            heading=_("Event Summary"),
        ),
        FieldPanel("country_events"),
        FieldPanel("chapters"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("description"),
        index.SearchField("region"),
    ]

    api_fields = [
        APIField("description"),
        APIField("event_start"),
        APIField("event_end"),
        APIField("region"),
        APIField("total_affected"),
        APIField("total_displaced"),
        APIField("total_deaths"),
    ]

    class Meta:
        verbose_name = _("Storyline")
        verbose_name_plural = _("Storylines")
