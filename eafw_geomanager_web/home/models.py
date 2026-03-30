from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail.api import APIField
from wagtail.api.v2.utils import get_full_url
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, Orderable
from wagtailcache.cache import WagtailCacheMixin, clear_cache
from wagtailmetadata.models import MetadataPageMixin
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail_color_panel.edit_handlers import NativeColorPanel
from .blocks import (
    InfoBlock,
    FeatureBlock,
    LinkGroupBlock,
    LinkBlock,
    SocialLinkBlock,
    MemberStateBlock,
    CTAButtonBlock,
    PartnerGroupBlock,
)
from .constants import GOOGLE_TRANSLATE_LANGUAGES


class Navbar(Page):
    max_count = 1
    template = "partials/navbar.html"
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = []

    logo = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Navbar Logo"),
        help_text=_("A high quality logo image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    logo_text_part_1 = models.CharField(
        max_length=100,
        blank=True,
        default="EAST AFRICA",
        verbose_name=_("Logo Text Part 1"),
        help_text=_("First part of the text-based logo."),
    )

    logo_text_part_2 = models.CharField(
        max_length=100,
        blank=True,
        default="HAZARDS",
        verbose_name=_("Logo Text Part 2"),
        help_text=_("Second part of the text-based logo"),
    )

    logo_text_part_3 = models.CharField(
        max_length=100,
        blank=True,
        default="WATCH",
        verbose_name=_("Logo Text Part 3"),
        help_text=_("Third part of the text-based logo"),
    )

    menu_items = StreamField(
        [
            ("link", LinkBlock()),
            ("dropdown", LinkGroupBlock()),
        ],
        blank=True,
        use_json_field=True,
        help_text=_("Add menu links and dropdown menus"),
    )

    background_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Navbar Background Image"),
        help_text=_("An optional background image for the navbar"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    background_opacity = models.IntegerField(
        default=55,
        verbose_name=_("Background Overlay Opacity"),
        help_text=_(
            "Overlay opacity over the background image (0 = fully transparent, 100 = fully opaque). Default is 55."
        ),
    )

    background_color = models.CharField(
        max_length=7,
        blank=True,
        default="",
        verbose_name=_("Background Color"),
        help_text=_("Custom background color. Overrides the site-wide theme navbar color when set."),
    )

    theme_colored_lines = models.BooleanField(
        default=False,
        verbose_name=_("Display Color Lines"),
        help_text=_(
            "If checked, colored lines will be drawn below the navbar. Add custom lines below, or leave empty for default theme colors."
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("logo"),
        MultiFieldPanel(
            [
                FieldPanel("logo_text_part_1"),
                FieldPanel("logo_text_part_2"),
                FieldPanel("logo_text_part_3"),
            ],
            heading=_("Text-based Logo (fallback when no image)"),
        ),
        FieldPanel("menu_items"),
        MultiFieldPanel(
            [
                FieldPanel("background_image"),
                FieldPanel("background_opacity"),
                NativeColorPanel("background_color"),
            ],
            heading=_("Background"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("theme_colored_lines"),
                InlinePanel("color_lines", label=_("Color Lines"), max_num=5),
            ],
            heading=_("Theme Colored Lines"),
        ),
    ]


class Footer(Page):
    max_count = 1
    template = "partials/footer.html"
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = []

    logo = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Footer Logo"),
        help_text=_("A high quality footer logo image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Logo Description"),
        help_text=_("A short text to display below the logo"),
    )

    sections = StreamField(
        [
            ("section", LinkGroupBlock()),
        ],
        blank=True,
        use_json_field=True,
        help_text=_("Add footer sections with custom titles and links"),
    )

    copyright_organization = models.CharField(
        max_length=100,
        default="ICPAC",
        verbose_name=_("Copyright Organization"),
        help_text=_("Organization name for copyright notice (e.g., 'ICPAC', 'Your Organization')"),
    )

    social_links = StreamField(
        [
            ("social_link", SocialLinkBlock()),
        ],
        blank=True,
        use_json_field=True,
        help_text=_("Add social media links with custom names and icons"),
    )

    background_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Footer Background Image"),
        help_text=_("An optional background image for the footer"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    background_opacity = models.IntegerField(
        default=55,
        verbose_name=_("Background Overlay Opacity"),
        help_text=_(
            "Overlay opacity over the background image (0 = fully transparent, 100 = fully opaque). Default is 55."
        ),
    )

    background_color = models.CharField(
        max_length=7,
        blank=True,
        default="",
        verbose_name=_("Background Color"),
        help_text=_("Custom background color. Overrides the site-wide theme footer color when set."),
    )

    theme_colored_lines = models.BooleanField(
        default=False,
        verbose_name=_("Display Color Lines"),
        help_text=_(
            "If checked, colored lines will be drawn above the footer. Add custom lines below, or leave empty for default theme colors."
        ),
    )

    cta = StreamField(
        [("cta_button", CTAButtonBlock())],
        blank=True,
        max_num=1,
        use_json_field=True,
        verbose_name=_("Call to Action Button"),
        help_text=_("Optional CTA button displayed prominently in the footer. Leave empty to hide."),
    )

    # editor interface panels
    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("logo"),
                FieldPanel("description"),
            ],
            heading=_("Logo & Description"),
        ),
        FieldPanel("sections"),
        FieldPanel("cta"),
        FieldPanel("copyright_organization"),
        FieldPanel("social_links"),
        MultiFieldPanel(
            [
                FieldPanel("background_image"),
                FieldPanel("background_opacity"),
                NativeColorPanel("background_color"),
            ],
            heading=_("Background"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("theme_colored_lines"),
                InlinePanel("color_lines", label=_("Color Lines"), max_num=5),
            ],
            heading=_("Theme Colored Lines"),
        ),
    ]


class AbstractColorLine(Orderable):
    """Abstract base for colored lines used in navbar and footer."""

    color = models.CharField(
        max_length=7,
        default="#034930",
        verbose_name=_("Line Color"),
        help_text=_("Pick a color for this line"),
    )

    panels = [NativeColorPanel("color")]

    class Meta(Orderable.Meta):
        abstract = True


class NavbarColorLine(AbstractColorLine):
    page = ParentalKey("Navbar", related_name="color_lines", on_delete=models.CASCADE)


class FooterColorLine(AbstractColorLine):
    page = ParentalKey("Footer", related_name="color_lines", on_delete=models.CASCADE)


class BannerImage(Orderable):
    """A banner image for the home page."""

    id = models.BigAutoField(primary_key=True)  # specify the primary key
    page = ParentalKey("HomePage", related_name="banner_images")
    image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Banner Image"),
        help_text=_("A high quality banner image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("image"),
    ]


class HomePage(MetadataPageMixin, WagtailCacheMixin, Page):
    template = "home/home_page.html"
    parent_page_type = ["wagtailcore.Page"]
    subpage_types = ["contact.ContactPage", "partners.PartnersPage", "home.ProjectPage"]
    max_count = 1

    banner_title = models.CharField(max_length=255, verbose_name=_("Banner Title"))
    banner_subtitle = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Banner Subtitle"))

    intro_text = RichTextField(
        blank=True,
        null=True,
        features=["bold"],
        verbose_name=_("Introduction text"),
        help_text=_("Introduction section description"),
    )
    intro_image = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Introduction Image"),
        help_text=_("A high quality image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    info_blocks = StreamField(
        [
            ("info", InfoBlock(label=_("Info"))),
        ],
        null=True,
        blank=True,
        use_json_field=True,
        verbose_name=_("Info Section"),
    )

    feature_blocks = StreamField(
        [
            (
                "feature",
                FeatureBlock(label=_("Feature")),
            ),
        ],
        null=True,
        blank=True,
        use_json_field=True,
        verbose_name=_("Features"),
    )

    show_member_states = models.BooleanField(
        default=False,
        verbose_name=_("Show Member States Section"),
        help_text=_("Display the Member States flags section on the homepage"),
    )

    member_states_title = models.CharField(
        max_length=255,
        default="Member States",
        blank=True,
        verbose_name=_("Member States Title"),
        help_text=_("Title for the member states section"),
    )

    member_states = StreamField(
        [
            ("member_state", MemberStateBlock()),
        ],
        null=True,
        blank=True,
        use_json_field=True,
        verbose_name=_("Member States"),
        help_text=_("Add member states with their flags"),
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("banner_title"),
                FieldPanel("banner_subtitle"),
                InlinePanel("banner_images", label=_("Banner Images"), max_num=10),
            ],
            heading=_("Banner Section"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("intro_text"),
                FieldPanel("intro_image"),
            ],
            heading=_("Introduction Section"),
        ),
        FieldPanel("info_blocks"),
        FieldPanel("feature_blocks"),
        MultiFieldPanel(
            [
                FieldPanel("show_member_states"),
                FieldPanel("member_states_title"),
                FieldPanel("member_states"),
            ],
            heading=_("Member States Section"),
        ),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super(HomePage, self).get_context(request, *args, **kwargs)
        # prevent system crash if geomanager is not properly configured/installed
        try:
            from geomanager.models import Category  # type: ignore
        except Exception:
            dataset_categories = None
        else:
            dataset_categories = Category.objects.filter(active=True, public=True)

        context.update({"dataset_categories": dataset_categories})
        mapviewer_url = get_full_url(request, reverse("mapview"))
        context.update({"mapviewer_url": mapviewer_url})

        footer = Footer.objects.live().first()
        context["footer"] = footer

        navbar = Navbar.objects.live().first()
        context["navbar"] = navbar

        # Get partners from PartnersPage
        from partners.models import PartnersPage

        partners_page = PartnersPage.objects.live().first()
        context["partners_page"] = partners_page

        return context


class ProjectPage(MetadataPageMixin, Page):
    template = "home/project_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types = []

    # Hero
    hero_image = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name=_("Hero Background Image"),
    )
    hero_title = models.CharField(max_length=255, verbose_name=_("Hero Title"))
    hero_subtitle = models.CharField(max_length=255, blank=True, verbose_name=_("Hero Subtitle"))
    project_logo = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name=_("Project Logo"),
    )
    description = RichTextField(
        blank=True, verbose_name=_("Project Description"),
        help_text=_("Full project description displayed below the hero"),
    )

    # Scope
    scope_key = models.CharField(
        max_length=50, blank=True, verbose_name=_("Scope Key"),
        help_text=_("Passed as ?scope= to mapviewer/reports for filtering (e.g., 'whca')"),
    )

    # Partners
    partner_groups = StreamField(
        [("partner_group", PartnerGroupBlock())],
        blank=True, use_json_field=True, verbose_name=_("Partner Groups"),
    )

    # Member countries
    member_countries_title = models.CharField(max_length=255, default="Member Countries", blank=True)
    member_countries = StreamField(
        [("member_state", MemberStateBlock())],
        blank=True, use_json_field=True, verbose_name=_("Member Countries"),
    )

    # CTA
    cta_buttons = StreamField(
        [("cta_button", CTAButtonBlock())],
        blank=True, use_json_field=True, verbose_name=_("Call to Action Buttons"),
    )

    # Contact & links
    contact_email = models.EmailField(blank=True, verbose_name=_("Contact Email"))
    project_url = models.URLField(blank=True, verbose_name=_("Project Website URL"))
    project_url_label = models.CharField(max_length=255, blank=True, default="More information here")

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("hero_image"),
            FieldPanel("project_logo"),
            FieldPanel("hero_title"),
            FieldPanel("hero_subtitle"),
        ], heading=_("Hero Section")),
        FieldPanel("description"),
        FieldPanel("scope_key"),
        FieldPanel("partner_groups"),
        MultiFieldPanel([
            FieldPanel("member_countries_title"),
            FieldPanel("member_countries"),
        ], heading=_("Member Countries")),
        FieldPanel("cta_buttons"),
        MultiFieldPanel([
            FieldPanel("contact_email"),
            FieldPanel("project_url"),
            FieldPanel("project_url_label"),
        ], heading=_("Contact & Links")),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        navbar = Navbar.objects.live().first()
        context["navbar"] = navbar
        footer = Footer.objects.live().first()
        context["footer"] = footer
        return context


class SiteTheme(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, help_text=_("Name for this theme"))
    primary_color = models.CharField(
        max_length=7, default="#034930", help_text=_("Main brand color (navbar, footer, primary buttons)")
    )
    secondary_color = models.CharField(
        max_length=7, default="#198754", help_text=_("Secondary color (buttons, highlights)")
    )
    accent_color = models.CharField(
        max_length=7, default="#fbc02d", help_text=_("Accent color (call-to-action elements)")
    )
    primary_text_color = models.CharField(max_length=7, default="#ffffff", help_text=_("Main text color"))
    secondary_text_color = models.CharField(max_length=7, default="#333333", help_text=_("Secondary text color"))
    background_color = models.CharField(max_length=7, default="#ffffff", help_text=_("Main background color"))
    is_active = models.BooleanField(default=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("is_active"),
        NativeColorPanel("primary_color"),
        NativeColorPanel("secondary_color"),
        NativeColorPanel("accent_color"),
        NativeColorPanel("primary_text_color"),
        NativeColorPanel("secondary_text_color"),
        NativeColorPanel("background_color"),
    ]

    def save(self, *args, **kwargs):
        if self.is_active:
            # Ensure only one active theme
            SiteTheme.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Active)" if self.is_active else self.name

    class Meta:
        verbose_name = "Site Theme"
        verbose_name_plural = "Site Themes"


@register_setting(icon="bars")
class SiteSettings(BaseGenericSetting):
    """
    Global site settings including tab icon.
    """

    tabicon = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Tab Icon"),
        help_text=_("Browser tab icon (favicon)."),
    )

    panels = [
        FieldPanel("tabicon"),
    ]

    class Meta:
        verbose_name = "Tab Icon"
        verbose_name_plural = "Tab Icons"


@register_setting(icon="link-external")
class MapserverConfig(BaseGenericSetting):
    """
    A single instance model for global mapserver and mapcache services configuration.
    """

    service_title: str = models.CharField(
        max_length=500,
        default=_("East Africa Hazards Watch (EAHW)"),
        help_text=_("descriptive text/title that can be use to identify this data system"),
    )
    service_purpose: str = models.TextField(
        default=_(
            "The East Africa Hazards Watch enables the monitoring of extreme events—such as droughts, cyclones, desert locust infestations, "
            + "heavy rainfall, floods, and crop failures—that can have severe and widespread impacts across the region"
        ),
        help_text=_("descriptive text that explains purpose and objectives of this service"),
    )
    service_provider: str = models.CharField(
        max_length=200,
        default=_("IGAD Climate Prediction and Applications Center (ICPAC)"),
        help_text=_("Name of service provider"),
    )
    provider_url: str = models.CharField(
        max_length=100, default=_("https://www.icpac.net"), help_text=_("Service provider's website URL")
    )
    office_country: str = models.CharField(
        max_length=100,
        default=_("Kenya"),
        help_text=_("Name of the country where service proivider offices are located"),
    )
    office_city: str = models.CharField(
        max_length=100, default=_("Naiobi"), help_text=_("Name of the city where service proivider offices are located")
    )
    physical_address: str = models.CharField(
        max_length=100,
        default=_("Ngong, Kibiko Area, Next to KHIBIT"),
        help_text=_("Physica address of the service proivider"),
    )
    email_address: str = models.CharField(
        max_length=100,
        default=_("disaster-risk-management@igad.int"),
        help_text=_("Contact email address through which service provider can be reached for support and feedback"),
    )
    contact_name: str = models.CharField(
        max_length=200,
        default=_("IGAD DRM Programme"),
        help_text=_("Name of contact division, unit or department within data proverder's organization"),
    )
    default_language: str = models.CharField(
        max_length=20, default=_("english"), help_text=_("Platform's default language. Any value is accepted")
    )
    service_fee: str = models.TextField(
        null=True,
        blank=True,
        default=_(
            "The Service is provided free of charge and on an 'AS IS' and 'AS AVAILABLE' basis. "
            + "We make no warranties, express or implied, regarding the service's reliability, availability, or accuracy."
        ),
        help_text=_("Service charge details if the service is provided at a fee"),
    )
    use_terms: str = models.TextField(
        blank=True,
        null=True,
        default="By accessing or using our Service, you agree to be bound by our Terms and Conditions of service. "
        + "If you disagree with any part of the terms, then you do not have permission to access the Service.",
        help_text="Terms of service use",
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("service_title"),
                FieldPanel("service_purpose"),
            ],
            heading=_("Service Description"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("service_provider"),
                FieldPanel("provider_url"),
                FieldPanel("contact_name"),
                FieldPanel("email_address"),
            ],
            heading=_("Service Provider Details"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("office_country"),
                FieldPanel("office_city"),
                FieldPanel("physical_address"),
            ],
            heading=_("Service Provider Address"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("default_language"),
                FieldPanel("service_fee"),
                FieldPanel("use_terms"),
            ],
            heading=_("WMS/WFS Service Details"),
        ),
    ]

    api_fields = [
        APIField("service_title"),
        APIField("service_purpose"),
        APIField("service_provider"),
        APIField("provider_url"),
        APIField("contact_name"),
        APIField("email_address"),
        APIField("office_country"),
        APIField("office_city"),
        APIField("physical_address"),
        APIField("default_language"),
        APIField("service_fee"),
        APIField("use_terms"),
    ]

    def __str__(self):
        return f"{self.service_provider} - {self.email_address}"

    class Meta:
        verbose_name = "WMS/WFS Configuration"
        verbose_name_plural = "WMS/WFS Configurations"


@register_setting(icon="globe")
class LanguageSettings(ClusterableModel, BaseGenericSetting):
    multilanguage_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Enable Multilanguage"),
        help_text=_("Toggle to enable Google Translate language switching on the site."),
    )

    panels = [
        FieldPanel("multilanguage_enabled"),
        InlinePanel("languages", label=_("Languages")),
    ]

    class Meta:
        verbose_name = _("Language Settings")
        verbose_name_plural = _("Language Settings")


class Language(Orderable):
    settings = ParentalKey(
        LanguageSettings,
        related_name="languages",
        on_delete=models.CASCADE,
    )
    language = models.CharField(
        max_length=10,
        choices=GOOGLE_TRANSLATE_LANGUAGES,
        verbose_name=_("Language"),
        help_text=_("Select a Google Translate supported language."),
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default Language"),
        help_text=_("Default site language. Only one language can be set as default."),
    )

    panels = [
        FieldPanel("language"),
        FieldPanel("is_default"),
    ]

    @property
    def code(self):
        return self.language

    @property
    def name(self):
        return self.get_language_display()

    def save(self, *args, **kwargs):
        if self.is_default:
            Language.objects.filter(settings=self.settings, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_language_display()

    class Meta(Orderable.Meta):
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")


@receiver(post_save, sender=LanguageSettings)
def clear_language_cache(sender, **kwargs):
    cache.delete("language_settings")
    clear_cache()
