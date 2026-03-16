import json

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail.api import APIField
from wagtail.api.v2.utils import get_full_url
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, Orderable
from wagtailcache.cache import WagtailCacheMixin
from wagtailmetadata.models import MetadataPageMixin
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail_color_panel.edit_handlers import NativeColorPanel
from wagtailiconchooser.utils import get_svg_sprite_for_icons
from .blocks import (
    InfoBlock, FeatureBlock, ActionCardBlock, LinkGroupBlock, LinkBlock, SocialLinkBlock,
    LogoItemBlock, CountryBlock
)
from .google_translate_languages import GOOGLE_TRANSLATE_LANGUAGE_CHOICES


class CategoryDescription(models.Model):
    """
    Stores descriptions for Geomanager categories.
    Links to geomanager.Category by category_id.
    """
    category_id = models.IntegerField(
        unique=True,
        verbose_name=_("Category ID"),
        help_text=_("ID of the Geomanager category"),
    )
    description = models.CharField(
        max_length=200,
        verbose_name=_("Description"),
        help_text=_("Short description for homepage display"),
    )

    class Meta:
        verbose_name = _("Category Description")
        verbose_name_plural = _("Category Descriptions")

    def __str__(self):
        return f"Category {self.category_id}: {self.description[:50]}"


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
        default="FLOOD",
        verbose_name=_("Logo Text Part 2"),
        help_text=_("Second part of the text-based logo"),
    )

    logo_text_part_3 = models.CharField(
        max_length=100,
        blank=True,
        default="WATCH FOR NILE",
        verbose_name=_("Logo Text Part 3"),
        help_text=_("Third part of the text-based logo"),
    )

    menu_items = StreamField(
        [
            ("link", LinkBlock()),
            ("dropdown", LinkGroupBlock()),
        ],
        blank=True,
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

    # Utility Bar Settings
    show_utility_bar = models.BooleanField(
        default=True,
        verbose_name=_("Show Utility Bar"),
        help_text=_("Display utility bar above the main navigation"),
    )
    utility_email = models.EmailField(
        blank=True,
        verbose_name=_("Contact Email"),
        help_text=_("Email address shown in utility bar"),
    )
    utility_phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Contact Phone"),
        help_text=_("Phone number shown in utility bar"),
    )
    utility_links = StreamField(
        [
            ("link", LinkBlock()),
        ],
        blank=True,
        verbose_name=_("Quick Links"),
        help_text=_("Quick links shown in utility bar"),
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
        MultiFieldPanel(
            [
                FieldPanel("show_utility_bar"),
                FieldPanel("utility_email"),
                FieldPanel("utility_phone"),
                FieldPanel("utility_links"),
            ],
            heading=_("Utility Bar"),
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
        
        help_text=_("Add footer sections with custom titles and links"),
    )

    member_countries = StreamField(
        [("country", CountryBlock())],
        blank=True,
        
        verbose_name=_("Member Countries"),
        help_text=_("Select countries - flags load automatically"),
    )

    partners = StreamField(
        [("partner", LogoItemBlock())],
        blank=True,
        
        verbose_name=_("Partners"),
        help_text=_("Add partner organizations with logos"),
    )

    partners_page_title = models.CharField(
        max_length=255,
        default="Our Partners",
        verbose_name=_("Partners Page Title"),
        help_text=_("Browser/title text for the dedicated partners page"),
    )

    partners_page_subtitle = models.TextField(
        blank=True,
        default="Working together to monitor and respond to flood risks across the East Africa region.",
        verbose_name=_("Partners Page Subtitle"),
        help_text=_("Intro subtitle shown at the top of the partners page"),
    )
    show_partners_page_subtitle = models.BooleanField(
        default=True,
        verbose_name=_("Show Partners Page Subtitle"),
        help_text=_("Enable or disable the subtitle on the partners page"),
    )

    partners_member_countries_title = models.CharField(
        max_length=255,
        default="ICPAC Partner Countries",
        verbose_name=_("Member Countries Section Title"),
        help_text=_("Heading for the member countries section on partners page"),
    )

    partners_member_countries_description = models.TextField(
        blank=True,
        default="ICPAC partner countries represented in the Flood Watch platform.",
        verbose_name=_("Member Countries Section Description"),
        help_text=_("Description under member countries heading on partners page"),
    )
    show_member_countries_intro = models.BooleanField(
        default=True,
        verbose_name=_("Show Member Countries Title/Description"),
        help_text=_("Enable or disable section title and description above member countries"),
    )

    partners_organizations_title = models.CharField(
        max_length=255,
        default="Our Partners",
        verbose_name=_("Partners Section Title"),
        help_text=_("Heading for the organizations section on partners page"),
    )

    partners_organizations_description = models.TextField(
        blank=True,
        default="Organizations collaborating with ICPAC on flood monitoring, preparedness, and response.",
        verbose_name=_("Partners Section Description"),
        help_text=_("Description under partners heading on partners page"),
    )
    show_partners_intro = models.BooleanField(
        default=True,
        verbose_name=_("Show Partners Title/Description"),
        help_text=_("Enable or disable section title and description above partner cards"),
    )

    partners_cta_title = models.CharField(
        max_length=255,
        default="Interested in Partnering?",
        verbose_name=_("CTA Title"),
        help_text=_("Title for the partners page call-to-action block"),
    )

    partners_cta_description = models.TextField(
        blank=True,
        default="We welcome collaboration with organizations committed to flood risk management and disaster preparedness in East Africa.",
        verbose_name=_("CTA Description"),
        help_text=_("Description text for the call-to-action block"),
    )

    partners_cta_button_text = models.CharField(
        max_length=120,
        default="Contact Us",
        verbose_name=_("CTA Button Text"),
        help_text=_("Label for the call-to-action button"),
    )

    partners_cta_button_url = models.CharField(
        max_length=255,
        default="mailto:disaster-risk-management@igad.int",
        verbose_name=_("CTA Button URL"),
        help_text=_("Link URL for the call-to-action button (mailto: or https://)"),
    )
    show_partners_cta = models.BooleanField(
        default=True,
        verbose_name=_("Show CTA Block"),
        help_text=_("Enable or disable the partners page call-to-action block"),
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
        
        help_text=_("Add social media links with custom names and icons"),
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
        MultiFieldPanel(
            [
                FieldPanel("show_member_countries_intro"),
                FieldPanel("partners_member_countries_title"),
                FieldPanel("partners_member_countries_description"),
                FieldPanel("member_countries"),
            ],
            heading=_("Member Countries (Partners Page)"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_partners_intro"),
                FieldPanel("partners_organizations_title"),
                FieldPanel("partners_organizations_description"),
                FieldPanel("partners"),
            ],
            heading=_("Partners (Partners Page)"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_partners_page_subtitle"),
                FieldPanel("partners_page_subtitle"),
                FieldPanel("show_partners_cta"),
                FieldPanel("partners_cta_title"),
                FieldPanel("partners_cta_description"),
                FieldPanel("partners_cta_button_text"),
                FieldPanel("partners_cta_button_url"),
            ],
            heading=_("Partners Page Intro & CTA"),
        ),
        FieldPanel("copyright_organization"),
        FieldPanel("social_links"),
    ]


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


# =============================================================================
# HOMEPAGE MAP CONFIGURATION - CMS-driven map elements
# =============================================================================

class MapLegendItem(Orderable):
    """CMS-configurable legend item for the homepage map."""

    page = ParentalKey("HomePage", related_name="map_legend_items")

    alert_level = models.CharField(
        max_length=20,
        choices=[
            ('emergency', _('Extreme')),
            ('alarm', _('Severe')),
            ('warning', _('Moderate')),
            ('normal', _('Normal')),
        ],
        verbose_name=_("Alert Level"),
        help_text=_("The alert level this legend item represents"),
    )
    label = models.CharField(
        max_length=100,
        verbose_name=_("Label"),
        help_text=_("Display label (e.g., 'Extreme: Severe flood risk')"),
    )
    icon = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Legend Icon"),
        help_text=_("Icon image for this legend item (same as used on map)"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("alert_level"),
        FieldPanel("label"),
        FieldPanel("icon"),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Map Legend Item")
        verbose_name_plural = _("Map Legend Items")


class MapExternalLink(Orderable):
    """CMS-configurable external link below the homepage map."""

    page = ParentalKey("HomePage", related_name="map_external_links")

    label = models.CharField(
        max_length=100,
        verbose_name=_("Link Label"),
        help_text=_("Text displayed on the button"),
    )
    url = models.CharField(
        max_length=500,
        verbose_name=_("URL"),
        help_text=_("Full URL or relative path (e.g., /reports/)"),
    )
    open_in_new_tab = models.BooleanField(
        default=True,
        verbose_name=_("Open in New Tab"),
    )
    button_color = models.CharField(
        max_length=7,
        default="#ff9800",
        verbose_name=_("Button Color"),
    )

    panels = [
        FieldPanel("label"),
        FieldPanel("url"),
        FieldPanel("open_in_new_tab"),
        FieldPanel("button_color"),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Map External Link")
        verbose_name_plural = _("Map External Links")


class MapCategory(Orderable):
    """CMS-configurable category for the homepage map menu (like 'Our Hazards Watch')."""

    page = ParentalKey("HomePage", related_name="map_categories")

    name = models.CharField(
        max_length=100,
        verbose_name=_("Category Name"),
        help_text=_("Display name for the category"),
    )
    icon = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Category Icon"),
        help_text=_("Icon image for the category"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    fa_icon_class = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("Font Awesome Class"),
        help_text=_("Optional Font Awesome classes, e.g. 'fa-solid fa-cloud-rain'"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether this category is enabled"),
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default Selected"),
        help_text=_("Whether this category is selected by default on page load"),
    )
    # Link to geomanager category if applicable
    geomanager_category_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Geomanager Category ID"),
        help_text=_("Optional: Link to a Geomanager category for layer data"),
    )

    # Layer rendering configuration
    RENDER_MODE_CHOICES = [
        ('points', _('GeoJSON Points')),
        ('wms-raster', _('WMS Raster')),
        ('impact-score', _('Impact Risk Score')),
    ]
    render_mode = models.CharField(
        max_length=20,
        choices=RENDER_MODE_CHOICES,
        default='points',
        verbose_name=_("Render Mode"),
        help_text=_("How this layer renders on the map"),
    )
    data_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Data URL"),
        help_text=_("GeoJSON endpoint URL (for points mode), e.g. /api/v1/multimodal/geojson/"),
    )
    wms_base_url = models.TextField(
        blank=True,
        verbose_name=_("WMS Base URL"),
        help_text=_(
            "Tile URL template (for wms-raster mode). "
            "Example: /cog-tiles/collections/{collection}/tiles/WebMercatorQuad/{z}/{x}/{y}.png?assets=data"
        ),
    )
    wms_layer_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("WMS Layer Name"),
        help_text=_("STAC collection ID or layer identifier, e.g. wrf_extreme_very_heavy"),
    )
    value_field = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Value Field"),
        help_text=_("GeoJSON property field for point values, e.g. 'daily_avg'"),
    )
    value_label = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Value Label"),
        help_text=_("Display label for the value, e.g. 'Discharge'"),
    )
    value_unit = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Value Unit"),
        help_text=_("Unit for values, e.g. 'm³/s'"),
    )
    unavailable_message = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Unavailable Message"),
        help_text=_("Message shown when this layer's data is unavailable"),
    )
    legend_items_json = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Legend Items"),
        help_text=_('JSON array of legend items, e.g. [{"label": "Extreme", "color": "#d32f2f"}]'),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("icon"),
                FieldPanel("fa_icon_class"),
                FieldPanel("is_active"),
                FieldPanel("is_default"),
                FieldPanel("geomanager_category_id"),
            ],
            heading=_("Basic Settings"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("render_mode"),
                FieldPanel("data_url"),
                FieldPanel("wms_base_url"),
                FieldPanel("wms_layer_name"),
            ],
            heading=_("Layer Data Source"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("value_field"),
                FieldPanel("value_label"),
                FieldPanel("value_unit"),
                FieldPanel("unavailable_message"),
                FieldPanel("legend_items_json"),
            ],
            heading=_("Display Settings"),
        ),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Map Category")
        verbose_name_plural = _("Map Categories")


class MapScope(Orderable):
    """CMS-configurable project scope for the homepage map filter (e.g. WHCA Project)."""

    page = ParentalKey("HomePage", related_name="map_scopes")

    name = models.CharField(
        max_length=100,
        verbose_name=_("Scope Name"),
        help_text=_("Button label, e.g. 'WHCA Project'"),
    )
    key = models.SlugField(
        max_length=50,
        verbose_name=_("Scope Key"),
        help_text=_("Unique key passed as ?scope= to the API, e.g. 'whca'"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether this scope button is shown"),
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default on Load"),
        help_text=_("If checked, this scope loads by default instead of 'All Countries'"),
    )

    # Country filtering
    country_codes_iso2 = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Country Codes (ISO-2)"),
        help_text=_("Comma-separated ISO-2 codes for member flag filtering, e.g. 'SD,SS,UG,ET,RW'"),
    )
    country_codes_iso3 = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Country Codes (ISO-3)"),
        help_text=_("Comma-separated ISO-3 codes for admin boundary filtering, e.g. 'ETH,RWA,SSD,SDN,UGA'"),
    )

    # Partner filtering
    partner_keys = models.TextField(
        blank=True,
        verbose_name=_("Partner Keys"),
        help_text=_("Comma-separated normalized partner name keys to show, e.g. 'wmo,wateratheart,netherlandsredcross'"),
    )

    # Display
    site_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Site Title Override"),
        help_text=_("Footer / site title when this scope is active, e.g. 'Nile River Basin Watch'. "
                     "Leave blank to keep 'East Africa Flood Watch'."),
    )
    country_section_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Country Section Title"),
        help_text=_("e.g. 'Nile Basin Flood Situation'"),
    )
    dashboard_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Dashboard Title"),
        help_text=_("e.g. 'Latest Situation of Nile Basin Flood Conditions'"),
    )

    # Visual
    show_basin_overlay = models.BooleanField(
        default=False,
        verbose_name=_("Show Basin Overlay"),
        help_text=_("Show the Nile basin boundary line when this scope is active"),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("key"),
                FieldPanel("is_active"),
                FieldPanel("is_default"),
            ],
            heading=_("Basic Settings"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("country_codes_iso2"),
                FieldPanel("country_codes_iso3"),
                FieldPanel("partner_keys"),
            ],
            heading=_("Country & Partner Filtering"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("site_title"),
                FieldPanel("country_section_title"),
                FieldPanel("dashboard_title"),
                FieldPanel("show_basin_overlay"),
            ],
            heading=_("Display Settings"),
        ),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Map Scope")
        verbose_name_plural = _("Map Scopes")


class HomePage(MetadataPageMixin, WagtailCacheMixin, Page):
    template = "home/home_page.html"
    parent_page_type = ["wagtailcore.Page"]
    subpage_types = []
    max_count = 1

    banner_title = models.CharField(max_length=255, verbose_name=_("Banner Title"))
    banner_subtitle = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Banner Subtitle"))
    hero_question = models.CharField(
        max_length=255,
        blank=True,
        default="Is there flood risk in East Africa?",
        verbose_name=_("Hero Question"),
        help_text=_("Question displayed in the Q&A style hero (e.g., 'Is there flood risk in East Africa?'). The answer is dynamically populated from forecast data."),
    )
    banner_button_text = models.CharField(
        max_length=50,
        default="Explore Map",
        verbose_name=_("Banner Button Text"),
        help_text=_("Text displayed on the hero banner button"),
    )
    banner_button_url = models.CharField(
        max_length=255,
        default="/mapviewer/",
        verbose_name=_("Banner Button URL"),
        help_text=_("URL the banner button links to"),
    )

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

    # Weather widget configuration
    show_weather_widget = models.BooleanField(
        default=False,
        verbose_name=_("Show Weather Widget"),
        help_text=_("Display weather forecast widget on homepage"),
    )
    weather_widget_title = models.CharField(
        max_length=100,
        blank=True,
        default="Weather Forecast",
        verbose_name=_("Weather Widget Title"),
    )

    info_blocks = StreamField(
        [
            ("info", InfoBlock(label=_("Info"))),
        ],
        null=True,
        blank=True,
        
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
        
        verbose_name=_("Features"),
    )

    what_you_can_do_title = models.CharField(
        max_length=100,
        default="What You Can Do",
        verbose_name=_("What You Can Do Section Title"),
        help_text=_("Title displayed above the action cards section"),
    )

    action_cards = StreamField(
        [
            ("action", ActionCardBlock(label=_("Action Card"))),
        ],
        null=True,
        blank=True,

        verbose_name=_("What You Can Do"),
        help_text=_("Action cards for the 'What You Can Do' section"),
    )

    # Mini-map preview configuration
    show_map_preview = models.BooleanField(
        default=True,
        verbose_name=_("Show Map Preview"),
        help_text=_("Display an interactive map preview on the homepage"),
    )
    map_preview_title = models.CharField(
        max_length=200,
        blank=True,
        default="Live Flood Monitoring",
        verbose_name=_("Map Preview Title"),
    )
    map_preview_subtitle = models.CharField(
        max_length=500,
        blank=True,
        default="Real-time flood extent and forecast data across East Africa",
        verbose_name=_("Map Preview Subtitle"),
    )

    # Mini-Map Widget Settings (Dashboard Layout)
    show_mini_map = models.BooleanField(
        default=True,
        verbose_name=_("Show Mini Map"),
        help_text=_("Display interactive mini-map widget on the homepage dashboard"),
    )
    mini_map_height = models.IntegerField(
        default=500,
        verbose_name=_("Mini Map Height (px)"),
        help_text=_("Height of the mini-map widget in pixels"),
    )
    mini_map_initial_zoom = models.IntegerField(
        default=4,
        verbose_name=_("Initial Zoom Level"),
        help_text=_("Initial zoom level for the mini-map (1-18)"),
    )
    mini_map_center_lat = models.FloatField(
        default=4.0,
        verbose_name=_("Center Latitude"),
        help_text=_("Initial center latitude for the mini-map"),
    )
    mini_map_center_lng = models.FloatField(
        default=38.0,
        verbose_name=_("Center Longitude"),
        help_text=_("Initial center longitude for the mini-map"),
    )

    # Country Cards Settings
    show_country_cards = models.BooleanField(
        default=True,
        verbose_name=_("Show Country Cards"),
        help_text=_("Display country cards alongside the mini-map"),
    )
    country_cards_title = models.CharField(
        max_length=200,
        default="Regional Flood Situation",
        verbose_name=_("Country Cards Title"),
        help_text=_("Title displayed above the country cards"),
    )
    max_country_cards = models.IntegerField(
        default=11,
        verbose_name=_("Max Country Cards"),
        help_text=_("Maximum number of country cards to display"),
    )
    # Homepage Layout Mode
    LAYOUT_CHOICES = [
        ('split', _('Split View (Map + Cards)')),
        ('stacked', _('Stacked View')),
    ]
    homepage_layout = models.CharField(
        max_length=20,
        choices=LAYOUT_CHOICES,
        default='split',
        verbose_name=_("Homepage Layout"),
        help_text=_("Layout mode for the homepage dashboard"),
    )

    # Dashboard Title (CMS-driven)
    dashboard_title = models.CharField(
        max_length=200,
        default="Latest Situation of Flood Conditions",
        verbose_name=_("Dashboard Title"),
        help_text=_("Main title displayed above the map (e.g., 'Latest Situation of Flood Conditions')"),
    )

    # Point Filter Mode (controls what points API returns)
    POINT_FILTER_CHOICES = [
        ('all', _('All Points')),
        ('active', _('Active Points Only (Moderate+)')),
        ('alarm', _('Severe and Above')),
        ('emergency', _('Extreme Only')),
    ]
    point_filter_mode = models.CharField(
        max_length=20,
        choices=POINT_FILTER_CHOICES,
        default='all',
        verbose_name=_("Point Filter"),
        help_text=_("Filter which forecast points are displayed on the map"),
    )

    # Category Menu Settings
    show_category_menu = models.BooleanField(
        default=False,
        verbose_name=_("Show Category Menu"),
        help_text=_("Display category menu inside the map (like 'Our Hazards Watch')"),
    )

    # Menu Style (ICPAC-web style vs current)
    MENU_STYLE_CHOICES = [
        ('card_list', _('Card List (Current)')),
        ('vertical_icons', _('Vertical Icons (ICPAC Style)')),
    ]
    category_menu_style = models.CharField(
        max_length=20,
        choices=MENU_STYLE_CHOICES,
        default='vertical_icons',
        verbose_name=_("Menu Style"),
        help_text=_("Visual style for the category menu"),
    )
    category_menu_active_color = models.CharField(
        max_length=7,
        default="#f7a600",
        verbose_name=_("Menu Active Color"),
        help_text=_("Color for active/selected menu item (hex code)"),
    )
    category_menu_bg_color = models.CharField(
        max_length=30,
        default="rgba(68, 65, 65, 0.84)",
        verbose_name=_("Menu Background Color"),
        help_text=_("Background color for the menu pill (hex or rgba)"),
    )

    # Map Logo Settings
    show_map_logo = models.BooleanField(
        default=True,
        verbose_name=_("Show Map Logo"),
        help_text=_("Display logo overlay on the map (bottom-left)"),
    )
    map_logo = models.ForeignKey(
        "wagtailimages.Image",
        verbose_name=_("Map Logo"),
        help_text=_("Logo displayed on the map (e.g., FloodWatch logo)"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    map_logo_link = models.CharField(
        max_length=255,
        blank=True,
        default="/mapviewer/",
        verbose_name=_("Map Logo Link"),
        help_text=_("URL the logo links to when clicked"),
    )

    # Legend Settings
    legend_title = models.CharField(
        max_length=100,
        default="Current Flood Alerts",
        verbose_name=_("Legend Title"),
        help_text=_("Title displayed above the map legend"),
    )
    legend_position = models.CharField(
        max_length=20,
        choices=[
            ('bottom-left', _('Bottom Left')),
            ('bottom-right', _('Bottom Right')),
            ('top-left', _('Top Left')),
            ('top-right', _('Top Right')),
        ],
        default='bottom-left',
        verbose_name=_("Legend Position"),
        help_text=_("Position of the legend on the map"),
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("banner_title"),
                FieldPanel("banner_button_text"),
                FieldPanel("banner_button_url"),
            ],
            heading=_("Header Settings"),
            help_text=_("Configure the compact header at the top of the homepage"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("dashboard_title"),
                FieldPanel("homepage_layout"),
                FieldPanel("show_mini_map"),
                FieldPanel("mini_map_initial_zoom"),
                FieldPanel("mini_map_center_lat"),
                FieldPanel("mini_map_center_lng"),
                FieldPanel("point_filter_mode"),
            ],
            heading=_("Mini-Map Widget"),
            help_text=_("Configure the interactive mini-map showing flood forecast points"),
        ),
        MultiFieldPanel(
            [
                InlinePanel("map_scopes", label=_("Project Scopes"), min_num=0, max_num=10),
            ],
            heading=_("Map Scope / Project Filter"),
            help_text=_("Define project scopes for the map filter (e.g. WHCA Project). 'All Countries' is always available. Mark one as default to load it on page open."),
        ),
        MultiFieldPanel(
            [
                FieldPanel("legend_title"),
                FieldPanel("legend_position"),
                InlinePanel("map_legend_items", label=_("Legend Items"), min_num=0, max_num=10),
            ],
            heading=_("Map Legend"),
            help_text=_("Configure the legend items displayed on the map. If empty, uses defaults from Multimodal Settings."),
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_map_logo"),
                FieldPanel("map_logo"),
                FieldPanel("map_logo_link"),
            ],
            heading=_("Map Logo"),
            help_text=_("Logo overlay displayed on the map (bottom-left corner)"),
        ),
        MultiFieldPanel(
            [
                InlinePanel("map_external_links", label=_("External Links"), min_num=0, max_num=5),
            ],
            heading=_("Map External Links"),
            help_text=_("Links displayed below the map (e.g., ICPAC Climate Portal, Flood Bulletins)"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_category_menu"),
                FieldPanel("category_menu_style"),
                FieldPanel("category_menu_active_color"),
                FieldPanel("category_menu_bg_color"),
                InlinePanel("map_categories", label=_("Categories"), min_num=0, max_num=10),
            ],
            heading=_("Category Menu"),
            help_text=_("Optional category menu inside the map (similar to 'Our Hazards Watch')"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_country_cards"),
                FieldPanel("country_cards_title"),
                FieldPanel("max_country_cards"),
            ],
            heading=_("Country Cards"),
            help_text=_("Configure the country cards panel (sorted by severity)"),
        ),
        # Hero Banner Section
        MultiFieldPanel(
            [
                FieldPanel("banner_subtitle"),
                InlinePanel("banner_images", label=_("Banner Images"), max_num=10),
            ],
            heading=_("1. Hero Banner"),
            help_text=_("Hero banner displayed at the top of the homepage. Uses banner_title from Header Settings."),
        ),
        # Info/About Section
        MultiFieldPanel(
            [
                FieldPanel("intro_text"),
                FieldPanel("intro_image"),
            ],
            heading=_("3. About Section"),
            help_text=_("Information section about the flood watch system (displayed after the map widget)"),
        ),
        # Additional Settings (collapsed)
        MultiFieldPanel(
            [
                FieldPanel("hero_question"),
                FieldPanel("show_weather_widget"),
                FieldPanel("weather_widget_title"),
                FieldPanel("show_map_preview"),
                FieldPanel("map_preview_title"),
                FieldPanel("map_preview_subtitle"),
                FieldPanel("mini_map_height"),
            ],
            heading=_("Additional Settings"),
            classname="collapsed",
        ),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super(HomePage, self).get_context(request, *args, **kwargs)
        # Load geomanager categories with descriptions for homepage display
        try:
            from geomanager.models import Category  # type: ignore
            categories = Category.objects.filter(active=True, public=True).order_by('order')
            # Get descriptions from our local model
            descriptions = {cd.category_id: cd.description for cd in CategoryDescription.objects.all()}
            # Attach descriptions to categories
            dataset_categories = []
            for cat in categories:
                cat.homepage_description = descriptions.get(cat.id, "")
                dataset_categories.append(cat)

            def normalize_menu_key(value):
                normalized = str(value or "").strip().lower().replace("_", " ")
                if "multimodal" in normalized:
                    return "multimodal"
                if "impact" in normalized:
                    return "impact"
                if "total rainfall" in normalized:
                    return "total-rainfall"
                if (
                    "extreme rainfall" in normalized
                    or "heavy rainfall" in normalized
                    or "rainfall" in normalized
                    or "weather" in normalized
                ):
                    return "extreme-rainfall"
                return None

            menu_label_by_key = {
                "multimodal": "Multimodal",
                "extreme-rainfall": "Extreme Rainfall",
                "total-rainfall": "Total Rainfall",
                "impact": "Impact",
            }
            preferred_order = ["multimodal", "extreme-rainfall", "total-rainfall"]

            geomanager_by_id = {cat.id: cat for cat in categories}
            geomanager_by_key = {}
            for cat in categories:
                key = normalize_menu_key(cat.title)
                if key and key not in geomanager_by_key:
                    geomanager_by_key[key] = cat

            mini_map_categories = []
            seen_keys = set()

            # Primary source: homepage CMS categories (if configured), but use linked geomanager title/icon
            for map_category in self.map_categories.all():
                if not map_category.is_active:
                    continue

                linked_category = geomanager_by_id.get(map_category.geomanager_category_id)
                source_name = linked_category.title if linked_category else map_category.name
                key = normalize_menu_key(source_name)
                if not key or key in seen_keys:
                    continue
                if key == "impact":
                    continue

                mini_map_categories.append({
                    "key": key,
                    "title": menu_label_by_key.get(key, source_name),
                    "icon_fa_class": map_category.fa_icon_class or "",
                    "icon_name": linked_category.icon if linked_category and linked_category.icon else "",
                    "icon_image": map_category.icon,
                    "category_id": linked_category.id if linked_category else map_category.geomanager_category_id,
                    "is_default": map_category.is_default,
                    "_map_category": map_category,
                })
                seen_keys.add(key)

            # Fallback source: mapviewer categories from geomanager CMS,
            # plus hardcoded defaults for minimap-only keys (e.g. total-rainfall)
            # that may be inactive in the mapviewer but still needed on the homepage.
            default_icons = {
                "multimodal": "urban-rural",
                "extreme-rainfall": "heavy-rain",
                "total-rainfall": "storm",
            }
            # Also check inactive categories for icon lookup
            all_categories_by_key = {}
            for cat in Category.objects.filter(public=True).order_by("order"):
                k = normalize_menu_key(cat.title)
                if k and k not in all_categories_by_key:
                    all_categories_by_key[k] = cat

            for key in preferred_order:
                if key in seen_keys:
                    continue
                linked_category = all_categories_by_key.get(key)
                icon_name = ""
                category_id = ""
                if linked_category:
                    icon_name = linked_category.icon or ""
                    category_id = linked_category.id
                if not icon_name:
                    icon_name = default_icons.get(key, "")
                mini_map_categories.append({
                    "key": key,
                    "title": menu_label_by_key.get(key, linked_category.title if linked_category else key),
                    "icon_fa_class": "",
                    "icon_name": icon_name,
                    "icon_image": None,
                    "category_id": category_id,
                    "is_default": key == "multimodal",
                })
                seen_keys.add(key)

            mini_map_categories = sorted(
                mini_map_categories,
                key=lambda item: preferred_order.index(item["key"]) if item["key"] in preferred_order else len(preferred_order)
            )

            # Ensure one default tab is set for initial map load
            if mini_map_categories and not any(item.get("is_default") for item in mini_map_categories):
                mini_map_categories[0]["is_default"] = True

            icon_names = [item["icon_name"] for item in mini_map_categories if item.get("icon_name")]
            map_category_svg_sprite = get_svg_sprite_for_icons(icon_names) if icon_names else ""
        except Exception:
            dataset_categories = None
            mini_map_categories = []
            map_category_svg_sprite = ""

        if not mini_map_categories:
            mini_map_categories = [
                {"key": "multimodal", "title": "Multimodal", "icon_fa_class": "", "icon_name": "", "icon_image": None, "category_id": "", "is_default": True},
                {"key": "extreme-rainfall", "title": "Extreme Rainfall", "icon_fa_class": "", "icon_name": "", "icon_image": None, "category_id": "", "is_default": False},
                {"key": "total-rainfall", "title": "Total Rainfall", "icon_fa_class": "", "icon_name": "", "icon_image": None, "category_id": "", "is_default": False},
            ]

        # Build CMS-driven layer configs for JavaScript (keyed by category key)
        layer_configs = {}
        for cat_item in mini_map_categories:
            mc = cat_item.get("_map_category")
            if not mc:
                continue
            key = cat_item["key"]
            layer_configs[key] = {
                "key": key,
                "label": cat_item["title"],
                "renderMode": mc.render_mode or "points",
                "dataUrl": mc.data_url or "",
                "wmsBaseUrl": mc.wms_base_url or "",
                "wmsLayerName": mc.wms_layer_name or "",
                "available": True,
                "valueLabel": mc.value_label or "",
                "valueField": mc.value_field or "",
                "valueUnit": mc.value_unit or "",
                "validationMessage": mc.unavailable_message or "",
                "legendItems": mc.legend_items_json if mc.legend_items_json else [],
            }

        # Strip internal _map_category references before passing to template
        for cat_item in mini_map_categories:
            cat_item.pop("_map_category", None)

        context.update({"dataset_categories": dataset_categories})
        context.update({"mini_map_categories": mini_map_categories})
        context.update({"map_category_svg_sprite": map_category_svg_sprite})
        context["mini_map_layer_configs_json"] = json.dumps(layer_configs) if layer_configs else "null"

        # Build scope configs from CMS
        scope_configs = {}
        default_scope_key = "all"
        map_scopes_list = []

        for scope_item in self.map_scopes.filter(is_active=True).order_by("sort_order"):
            key = scope_item.key
            iso2_list = [c.strip().upper() for c in (scope_item.country_codes_iso2 or "").split(",") if c.strip()]
            iso3_list = [c.strip().upper() for c in (scope_item.country_codes_iso3 or "").split(",") if c.strip()]
            partner_list = [
                p.strip().lower().replace(" ", "")
                for p in (scope_item.partner_keys or "").split(",")
                if p.strip()
            ]

            scope_configs[key] = {
                "key": key,
                "label": scope_item.name,
                "countryCodes": iso2_list,
                "admin0Codes": iso3_list,
                "partnerKeys": partner_list,
                "siteTitle": scope_item.site_title or "",
                "countrySectionTitle": scope_item.country_section_title or "",
                "dashboardTitle": scope_item.dashboard_title or "",
                "showBasinOverlay": scope_item.show_basin_overlay,
            }
            map_scopes_list.append({"key": key, "name": scope_item.name})

            if scope_item.is_default:
                default_scope_key = key

        context["map_scopes_json"] = json.dumps(scope_configs) if scope_configs else "null"
        context["default_scope_key"] = default_scope_key
        context["map_scopes"] = map_scopes_list

        mapviewer_url = get_full_url(request, reverse("mapview"))
        context.update({"mapviewer_url": mapviewer_url})

        # Load MultimodalClusterSettings for alert thresholds and colors
        multimodal_settings = MultimodalClusterSettings.objects.first()
        context["multimodal_settings"] = multimodal_settings

        footer = Footer.objects.live().first()
        context["footer"] = footer

        navbar = Navbar.objects.live().first()
        context["navbar"] = navbar

        # Add weather forecast data
        try:
            from forecastmanager.models import CityForecast
            from forecastmanager.forecast_settings import ForecastSetting
            from django.utils import timezone

            today = timezone.localdate()
            # Get today's forecasts for all cities
            forecasts = CityForecast.objects.filter(
                parent__forecast_date=today
            ).select_related('city', 'condition', 'parent', 'parent__effective_period').order_by('city__name')

            # Get forecast settings for display options
            fm_settings = ForecastSetting.for_request(request)
            show_conditions_label = fm_settings.show_conditions_label_on_widget if fm_settings else True

            context["forecasts"] = forecasts
            context["show_conditions_label"] = show_conditions_label
        except Exception:
            # Forecastmanager not installed or configured
            context["forecasts"] = None
            context["show_conditions_label"] = True

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

    # Wave animation settings (water-themed visual effects)
    enable_wave_animation = models.BooleanField(
        default=False,
        verbose_name=_("Enable Wave Animation"),
        help_text=_("Show animated wave effect on the homepage hero section"),
    )
    wave_color_1 = models.CharField(
        max_length=7,
        default="#e0f7fa",
        verbose_name=_("Wave Color 1 (Lightest)"),
        help_text=_("Lightest wave color - top layer"),
    )
    wave_color_2 = models.CharField(
        max_length=7,
        default="#4dd0e1",
        verbose_name=_("Wave Color 2 (Middle)"),
        help_text=_("Middle wave color"),
    )
    wave_color_3 = models.CharField(
        max_length=7,
        default="#0097a7",
        verbose_name=_("Wave Color 3 (Darkest)"),
        help_text=_("Darkest wave color - bottom layer"),
    )
    wave_opacity = models.IntegerField(
        default=60,
        verbose_name=_("Wave Opacity (%)"),
        help_text=_("Opacity of the wave animation (0-100)"),
    )
    wave_height = models.IntegerField(
        default=150,
        verbose_name=_("Wave Height (px)"),
        help_text=_("Height of the wave animation area in pixels"),
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("is_active"),
        MultiFieldPanel(
            [
                NativeColorPanel("primary_color"),
                NativeColorPanel("secondary_color"),
                NativeColorPanel("accent_color"),
                NativeColorPanel("primary_text_color"),
                NativeColorPanel("secondary_text_color"),
                NativeColorPanel("background_color"),
            ],
            heading=_("Theme Colors"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("enable_wave_animation"),
                NativeColorPanel("wave_color_1"),
                NativeColorPanel("wave_color_2"),
                NativeColorPanel("wave_color_3"),
                FieldPanel("wave_opacity"),
                FieldPanel("wave_height"),
            ],
            heading=_("Wave Animation Settings"),
            help_text=_("Configure water-themed wave animation for the homepage"),
        ),
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
        default=_("ICPAC Climate Prediction and Applications Centre"),
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
        default=_("ICPAC Disaster Risk Management Programme"),
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


# =============================================================================
# LANGUAGE SETTINGS - CMS configurable languages
# =============================================================================

# Available language choices - all Google Translate supported languages.
LANGUAGE_CHOICES = GOOGLE_TRANSLATE_LANGUAGE_CHOICES


class EnabledLanguage(Orderable):
    """Individual enabled language for the site."""

    language_setting = ParentalKey(
        "home.LanguageSettings",
        on_delete=models.CASCADE,
        related_name="enabled_languages",
    )

    language_code = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        verbose_name=_("Language"),
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default Language"),
        help_text=_("Check if this is the default site language"),
    )

    panels = [
        FieldPanel("language_code"),
        FieldPanel("is_default"),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Enabled Language")
        verbose_name_plural = _("Enabled Languages")

    def __str__(self):
        return dict(LANGUAGE_CHOICES).get(self.language_code, self.language_code)


@register_setting(icon="globe")
class LanguageSettings(ClusterableModel, BaseGenericSetting):
    """
    CMS-configurable language settings.
    Admins can enable/disable languages for the site.
    """

    panels = [
        MultiFieldPanel(
            [
                InlinePanel(
                    "enabled_languages",
                    label=_("Enabled Language"),
                    min_num=1,
                ),
            ],
            heading=_("Site Languages"),
            help_text=_("Add languages available on the site. Mark one as default."),
        ),
    ]

    class Meta:
        verbose_name = _("Language Settings")
        verbose_name_plural = _("Language Settings")

    def get_enabled_languages(self):
        """Return list of (code, name) tuples for enabled languages."""
        return [
            (lang.language_code, dict(LANGUAGE_CHOICES).get(lang.language_code, lang.language_code))
            for lang in self.enabled_languages.all()
        ]

    def get_default_language(self):
        """Return the default language code."""
        default = self.enabled_languages.filter(is_default=True).first()
        if default:
            return default.language_code
        # Fallback to first enabled language
        first = self.enabled_languages.first()
        return first.language_code if first else "en"


@register_setting(icon="warning")
class MultimodalClusterSettings(BaseGenericSetting):
    """
    CMS-configurable settings for multimodal forecast point clustering.
    Controls alert thresholds, colors, and cluster behavior on the map.
    """

    # Enable/disable clustering
    enable_clustering = models.BooleanField(
        default=True,
        verbose_name=_("Enable Clustering"),
        help_text=_("Enable clustering of multimodal forecast points on the map"),
    )

    # Alert thresholds (discharge in m³/s)
    warning_threshold = models.FloatField(
        default=300.0,
        verbose_name=_("Moderate Threshold (m³/s)"),
        help_text=_("Daily average discharge above this value triggers Moderate (Warning) level"),
    )
    alarm_threshold = models.FloatField(
        default=500.0,
        verbose_name=_("Severe Threshold (m³/s)"),
        help_text=_("Daily average discharge above this value triggers Severe (Alarm) level"),
    )
    emergency_threshold = models.FloatField(
        default=750.0,
        verbose_name=_("Extreme Threshold (m³/s)"),
        help_text=_("Daily average discharge above this value triggers Extreme (Emergency) level"),
    )

    # Alert colors
    normal_color = models.CharField(
        max_length=7,
        default="#b0bec5",
        verbose_name=_("Normal Color"),
        help_text=_("Color for normal alert level (hex format, e.g., #b0bec5)"),
    )
    warning_color = models.CharField(
        max_length=7,
        default="#b8f0f0",
        verbose_name=_("Moderate Color"),
        help_text=_("Color for Moderate (Warning) alert level (hex format, e.g., #b8f0f0)"),
    )
    alarm_color = models.CharField(
        max_length=7,
        default="#2f83d2",
        verbose_name=_("Severe Color"),
        help_text=_("Color for Severe (Alarm) alert level (hex format, e.g., #2f83d2)"),
    )
    emergency_color = models.CharField(
        max_length=7,
        default="#1e1a97",
        verbose_name=_("Extreme Color"),
        help_text=_("Color for Extreme (Emergency) alert level (hex format, e.g., #1e1a97)"),
    )

    # Cluster configuration
    cluster_max_zoom = models.IntegerField(
        default=12,
        verbose_name=_("Cluster Max Zoom"),
        help_text=_("Maximum zoom level at which points are clustered (0-22)"),
    )
    cluster_radius = models.IntegerField(
        default=50,
        verbose_name=_("Cluster Radius"),
        help_text=_("Radius in pixels for grouping points into clusters"),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("enable_clustering"),
            ],
            heading=_("General"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("warning_threshold"),
                FieldPanel("alarm_threshold"),
                FieldPanel("emergency_threshold"),
            ],
            heading=_("Alert Thresholds"),
            help_text=_("Configure discharge thresholds (m³/s) for each alert level"),
        ),
        MultiFieldPanel(
            [
                NativeColorPanel("normal_color"),
                NativeColorPanel("warning_color"),
                NativeColorPanel("alarm_color"),
                NativeColorPanel("emergency_color"),
            ],
            heading=_("Alert Colors"),
            help_text=_("Configure colors for each alert level"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("cluster_max_zoom"),
                FieldPanel("cluster_radius"),
            ],
            heading=_("Cluster Configuration"),
        ),
    ]

    class Meta:
        verbose_name = _("Multimodal Cluster Settings")
        verbose_name_plural = _("Multimodal Cluster Settings")

    def get_config(self):
        """Return settings as a dictionary for the frontend."""
        return {
            "enableClustering": self.enable_clustering,
            "thresholds": {
                "warning": self.warning_threshold,
                "alarm": self.alarm_threshold,
                "emergency": self.emergency_threshold,
            },
            "colors": {
                "normal": self.normal_color,
                "warning": self.warning_color,
                "alarm": self.alarm_color,
                "emergency": self.emergency_color,
            },
            "clusterMaxZoom": self.cluster_max_zoom,
            "clusterRadius": self.cluster_radius,
            # Include dynamic style and animations
            "layerStyle": self.get_layer_style(),
            "animations": self.get_animation_config(),
        }

    def get_layer_style(self, source_layer="public.multimodal_points_clustered"):
        """
        Generate MapLibre layer style dynamically based on CMS settings.
        Uses circle layer with dynamic colors based on alert_level property.
        """
        return [
            {
                "id": "multimodal-circles",
                "type": "circle",
                "source-layer": source_layer,
                "paint": {
                    # Dynamic radius based on cluster size
                    "circle-radius": [
                        "interpolate", ["linear"], ["zoom"],
                        3, ["case",
                            [">", ["get", "point_count"], 50], 12,
                            [">", ["get", "point_count"], 10], 10,
                            [">", ["get", "point_count"], 1], 8,
                            6
                        ],
                        10, ["case",
                            [">", ["get", "point_count"], 50], 18,
                            [">", ["get", "point_count"], 10], 14,
                            [">", ["get", "point_count"], 1], 10,
                            8
                        ]
                    ],
                    # Dynamic color based on alert_level
                    "circle-color": [
                        "match", ["get", "alert_level"],
                        "emergency", self.emergency_color,
                        "alarm", self.alarm_color,
                        "warning", self.warning_color,
                        "normal", self.normal_color,
                        self.normal_color  # default
                    ],
                    "circle-stroke-width": 2,
                    "circle-stroke-color": "#ffffff",
                    "circle-opacity": 0.9,
                },
                "metadata": {
                    "position": "top",
                    "interactive": True,
                }
            },
            # Label layer for cluster count
            {
                "id": "multimodal-labels",
                "type": "symbol",
                "source-layer": source_layer,
                "filter": [">", ["get", "point_count"], 1],
                "layout": {
                    "text-field": ["to-string", ["get", "point_count"]],
                    "text-size": 11,
                    "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
                    "text-allow-overlap": True,
                },
                "paint": {
                    "text-color": "#ffffff",
                    "text-halo-color": "rgba(0,0,0,0.5)",
                    "text-halo-width": 1,
                }
            }
        ]

    def get_animation_config(self):
        """
        Return CSS animation configuration for markers.
        Animations are disabled for mapviewer to keep points static.
        """
        return {
            "enabled": False,
            "keyframes": {},
            "durations": {},
            "classes": {
                "warning": "",
                "alarm": "",
                "emergency": "",
            },
            "css": "",
        }

    def _generate_animation_css(self):
        """Generate CSS string for marker animations."""
        return """
@keyframes blink-warning {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
@keyframes blink-alarm {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
@keyframes blink-emergency {
  0%, 100% { opacity: 1; }
  25% { opacity: 0.2; }
  50% { opacity: 1; }
  75% { opacity: 0.2; }
}
.animate-blink-warning { animation: blink-warning 2s ease-in-out infinite; }
.animate-blink-alarm { animation: blink-alarm 1.5s ease-in-out infinite; }
.animate-blink-emergency { animation: blink-emergency 1s ease-in-out infinite; }
"""


# =============================================================================
# MULTIMODAL DATA UPLOAD - CMS admin interface for uploading forecast data
# =============================================================================

DATA_SOURCE_CHOICES = [
    ("upload", _("File Upload")),
    ("ftp", _("FTP Server")),
    ("drive", _("Google Drive")),
]

UPLOAD_STATUS_CHOICES = [
    ("pending", _("Pending")),
    ("processing", _("Processing")),
    ("completed", _("Completed")),
    ("failed", _("Failed")),
]


class MultimodalDataUpload(models.Model):
    """
    CMS model for uploading and processing multimodal forecast data.
    Users can upload CSV files (individual or ZIP) and shapefiles.
    System auto-merges and creates GeoJSON for visualization.
    """

    title = models.CharField(
        max_length=255,
        verbose_name=_("Title"),
        help_text=_("Descriptive title for this upload batch"),
    )

    data_date = models.DateField(
        verbose_name=_("Forecast Date"),
        help_text=_("Date of the forecast data"),
    )

    source = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="upload",
        verbose_name=_("Data Source"),
    )

    # File uploads
    csv_file = models.FileField(
        upload_to="multimodal/csv/",
        blank=True,
        null=True,
        verbose_name=_("CSV File"),
        help_text=_("Single Zone CSV file or ZIP containing multiple Zone*.csv files"),
    )

    shapefile = models.FileField(
        upload_to="multimodal/shapefiles/",
        blank=True,
        null=True,
        verbose_name=_("Control Points Shapefile"),
        help_text=_("ZIP file containing shapefile (.shp, .shx, .dbf, .prj) for control points"),
    )

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=UPLOAD_STATUS_CHOICES,
        default="pending",
        verbose_name=_("Status"),
    )

    processing_log = models.TextField(
        blank=True,
        verbose_name=_("Processing Log"),
        help_text=_("Log messages from processing"),
    )

    # Results
    feature_count = models.IntegerField(
        default=0,
        verbose_name=_("Total Features"),
    )

    matched_count = models.IntegerField(
        default=0,
        verbose_name=_("Features with Data"),
    )

    geojson_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Generated GeoJSON"),
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="multimodal_uploads",
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
                FieldPanel("data_date"),
                FieldPanel("source"),
            ],
            heading=_("Basic Information"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("csv_file"),
                FieldPanel("shapefile"),
            ],
            heading=_("File Uploads"),
            help_text=_("Upload CSV files and optional shapefile for control points"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("status", read_only=True),
                FieldPanel("feature_count", read_only=True),
                FieldPanel("matched_count", read_only=True),
                FieldPanel("processing_log", read_only=True),
            ],
            heading=_("Processing Status"),
        ),
    ]

    class Meta:
        verbose_name = _("Multimodal Data Upload")
        verbose_name_plural = _("Multimodal Data Uploads")
        ordering = ["-data_date", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.data_date}"

    def process_upload(self):
        """Process uploaded files and create GeoJSON."""
        from django.core.management import call_command
        from io import StringIO
        import zipfile
        import csv
        import json
        from django.db import connection

        self.status = "processing"
        self.processing_log = ""
        self.save()

        try:
            from django.utils import timezone
            log_lines = []
            log_lines.append(f"Starting processing at {timezone.now()}")

            # Load control points
            control_points = self._load_control_points()
            log_lines.append(f"Loaded {len(control_points)} control points")

            # Parse CSV files
            zone_data = self._parse_csv_files()
            log_lines.append(f"Parsed {len(zone_data)} zone files")

            # Create GeoJSON
            geojson = self._create_geojson(zone_data, control_points)
            log_lines.append(f"Created GeoJSON with {len(geojson['features'])} features")

            # Save results
            self.geojson_data = geojson
            self.feature_count = len(geojson['features'])
            self.matched_count = sum(1 for f in geojson['features'] if f['properties'].get('has_data'))
            self.status = "completed"
            self.processing_log = "\n".join(log_lines)
            self.save()

            # Also save to the main forecast table
            self._save_to_forecast_table(geojson)
            log_lines.append("Saved to forecast table")

            return True

        except Exception as e:
            self.status = "failed"
            self.processing_log = f"Error: {str(e)}"
            self.save()
            return False

    def _load_control_points(self):
        """Load control points from database or uploaded shapefile."""
        from django.db import connection
        import json

        # If shapefile uploaded, use that
        if self.shapefile:
            return self._load_shapefile_points()

        # Otherwise use database
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    point_id, gridcode, admin_name, x, y, zone, is_node,
                    ST_AsGeoJSON(geom) as geometry
                FROM multimodal_control_points
                ORDER BY zone, gridcode
            """)

            control_points = {}
            for row in cursor.fetchall():
                point_id, gridcode, admin_name, x, y, zone, is_node, geom_json = row
                key = (zone, gridcode)
                control_points[key] = {
                    'point_id': point_id,
                    'gridcode': gridcode,
                    'admin_name': admin_name,
                    'x': x, 'y': y,
                    'zone': zone,
                    'is_node': is_node,
                    'geometry': json.loads(geom_json)
                }

        return control_points

    def _load_shapefile_points(self):
        """Load control points from uploaded shapefile ZIP."""
        import tempfile
        import zipfile
        import json

        try:
            from django.contrib.gis.gdal import DataSource
        except ImportError:
            raise Exception("GDAL not available for shapefile processing")

        control_points = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract ZIP
            with zipfile.ZipFile(self.shapefile.path, 'r') as zf:
                zf.extractall(tmpdir)

            # Find .shp file
            import os
            shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
            if not shp_files:
                raise Exception("No .shp file found in ZIP")

            shp_path = os.path.join(tmpdir, shp_files[0])
            ds = DataSource(shp_path)
            layer = ds[0]

            for feature in layer:
                zone = feature.get('Zone') or feature.get('zone') or 1
                gridcode = feature.get('GRIDCODE') or feature.get('gridcode') or feature.get('ID')
                key = (int(zone), int(gridcode))

                geom = feature.geom
                control_points[key] = {
                    'point_id': gridcode,
                    'gridcode': int(gridcode),
                    'admin_name': feature.get('admin_name') or feature.get('NAME') or '',
                    'x': geom.x if hasattr(geom, 'x') else geom.centroid.x,
                    'y': geom.y if hasattr(geom, 'y') else geom.centroid.y,
                    'zone': int(zone),
                    'is_node': feature.get('is_node') or False,
                    'geometry': json.loads(geom.json)
                }

        return control_points

    def _parse_csv_files(self):
        """Parse uploaded CSV file(s)."""
        import zipfile
        import csv
        from io import StringIO

        zone_data = {}

        if not self.csv_file:
            return zone_data

        file_path = self.csv_file.path

        # Check if ZIP file
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.csv') and 'Zone' in name:
                        # Extract zone number from filename
                        import re
                        match = re.search(r'Zone(\d+)', name, re.IGNORECASE)
                        if match:
                            zone_num = int(match.group(1))
                            content = zf.read(name).decode('utf-8')
                            zone_data[zone_num] = self._parse_csv_content(content, zone_num)
        else:
            # Single CSV file
            with open(file_path, 'r') as f:
                content = f.read()
            # Assume Zone 1 if not specified
            zone_data[1] = self._parse_csv_content(content, 1)

        return zone_data

    def _parse_csv_content(self, content, zone_num):
        """Parse CSV content and return forecast data by gridcode."""
        import csv
        from io import StringIO

        data = {}  # {gridcode: [forecast_records]}
        reader = csv.DictReader(StringIO(content))

        for row in reader:
            try:
                gridcode = int(row.get('GRIDCODE', 0))
                if gridcode not in data:
                    data[gridcode] = []

                forecast_record = {}
                for col, value in row.items():
                    forecast_record[col] = value if value else '0'
                data[gridcode].append(forecast_record)

            except (ValueError, TypeError):
                continue

        return data

    def _create_geojson(self, zone_data, control_points):
        """Create GeoJSON from parsed data and control points."""
        features = []

        for key, point in control_points.items():
            zone, gridcode = key
            forecasts = zone_data.get(zone, {}).get(gridcode, [])

            feature = {
                'type': 'Feature',
                'geometry': point['geometry'],
                'properties': {
                    'point_id': point['point_id'],
                    'gridcode': point['gridcode'],
                    'admin_name': point['admin_name'],
                    'zone': point['zone'],
                    'x': point['x'],
                    'y': point['y'],
                    'is_node': point.get('is_node', False),
                    'has_data': len(forecasts) > 0,
                    'forecasts': forecasts
                }
            }
            features.append(feature)

        return {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'date': self.data_date.strftime('%Y-%m-%d'),
                'total_points': len(features),
                'upload_id': self.id
            }
        }

    def _save_to_forecast_table(self, geojson):
        """Save processed GeoJSON to the forecast table."""
        from django.db import connection
        import json

        date_str = self.data_date.strftime('%Y%m%d')

        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO home_multimodal_forecast_geojson (
                    data_date, date_string, geojson_data,
                    feature_count, matched_count, processed_by,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (data_date) DO UPDATE SET
                    geojson_data = EXCLUDED.geojson_data,
                    feature_count = EXCLUDED.feature_count,
                    matched_count = EXCLUDED.matched_count,
                    processed_by = EXCLUDED.processed_by,
                    updated_at = NOW()
            """, [
                self.data_date,
                date_str,
                json.dumps(geojson),
                self.feature_count,
                self.matched_count,
                f'cms_upload_{self.id}'
            ])


# =============================================================================
# UNMANAGED MODELS - Read-only views of gha schema tables
# =============================================================================

EXPERT_TYPE_CHOICES = [
    ('hydrologist', _('Hydrologist')),
    ('meteorologist', _('Meteorologist')),
]

RISK_LEVEL_CHOICES = [
    ('normal', _('Normal')),
    ('watch', _('Watch')),
    ('warning', _('Warning')),
    ('alarm', _('Alarm')),
    ('emergency', _('Emergency')),
]


class ExpertAssessment(models.Model):
    """Read-only view of gha.expert_assessments table."""

    expert_type = models.CharField(max_length=20, choices=EXPERT_TYPE_CHOICES)
    assessment_date = models.DateField()
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    country_code = models.CharField(max_length=10, default='REGION')
    country_name = models.CharField(max_length=100, null=True, blank=True)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='normal')
    assessment_comment = models.TextField()
    affected_areas = models.TextField(null=True, blank=True)
    recommendations = models.TextField(null=True, blank=True)
    created_by = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(null=True, blank=True, default=False)

    class Meta:
        managed = False
        db_table = 'expert_assessments'
        verbose_name = _('Expert Assessment')
        verbose_name_plural = _('Expert Assessments')
        ordering = ['-assessment_date', '-created_at']

    def __str__(self):
        return f"{self.get_expert_type_display()} - {self.country_name or 'Region'} ({self.assessment_date})"

    @property
    def flag_url(self):
        if self.country_code and self.country_code != 'REGION':
            return f"https://flagcdn.com/w40/{self.country_code.lower()}.png"
        return None


class DistrictRiskLevel(models.Model):
    """Read-only view of gha.district_risk_levels table."""

    expert_type = models.CharField(max_length=20, choices=EXPERT_TYPE_CHOICES)
    assessment_date = models.DateField()
    country = models.CharField(max_length=100)
    admin1 = models.CharField(max_length=100, verbose_name=_('Admin Level 1'))
    admin2 = models.CharField(max_length=100, verbose_name=_('Admin Level 2'))
    gid_2 = models.CharField(max_length=50, null=True, blank=True, verbose_name=_('GID 2'))
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='normal')
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'district_risk_levels'
        verbose_name = _('District Risk Level')
        verbose_name_plural = _('District Risk Levels')
        ordering = ['-assessment_date', 'country', 'admin1']

    def __str__(self):
        return f"{self.country} - {self.admin1}/{self.admin2} ({self.risk_level})"


class ReportSnapshot(models.Model):
    """Read-only view of gha.report_snapshots table."""

    assessment_id = models.IntegerField(unique=True)
    snapshot_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'report_snapshots'
        verbose_name = _('Report Snapshot')
        verbose_name_plural = _('Report Snapshots')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Snapshot for assessment #{self.assessment_id}"
