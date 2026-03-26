from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtailcache.cache import WagtailCacheMixin
from wagtailmetadata.models import MetadataPageMixin

from home.blocks import CTAButtonBlock
from .blocks import PartnerBlock


class PartnersPage(MetadataPageMixin, WagtailCacheMixin, Page):
    """A page to display partners and collaborators."""

    template = "partners/partners_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types = []
    max_count = 1

    # Hero
    banner_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Banner Image"),
        help_text=_("Full-width image displayed at the top of the page."),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    page_title = models.CharField(
        max_length=255,
        default="Our Partners",
        verbose_name=_("Page Title"),
        help_text=_("Main heading for the partners page"),
    )

    page_subtitle = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Page Subtitle"),
        help_text=_("Brief introduction or description for the partners page"),
    )

    partners = StreamField(
        [
            ("partner", PartnerBlock()),
        ],
        null=True,
        blank=True,
        use_json_field=True,
        verbose_name=_("Partners"),
        help_text=_("Add partner organizations"),
    )

    cta = StreamField(
        [("cta_button", CTAButtonBlock())],
        blank=True,
        max_num=1,
        use_json_field=True,
        verbose_name=_("Call to Action Button"),
        help_text=_("Optional CTA button displayed below the partner cards. Leave empty to hide."),
    )

    content_panels = Page.content_panels + [
        FieldPanel("banner_image"),
        FieldPanel("page_title"),
        FieldPanel("page_subtitle"),
        FieldPanel("partners"),
        FieldPanel("cta"),
    ]

    def get_context(self, request, *args, **kwargs):
        from home.models import Footer, Navbar

        context = super(PartnersPage, self).get_context(request, *args, **kwargs)

        footer = Footer.objects.live().first()
        context["footer"] = footer

        navbar = Navbar.objects.live().first()
        context["navbar"] = navbar

        return context
