from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtailiconchooser.blocks import IconChooserBlock


class InfoBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        max_length=100,
        label=_("Section Title"),
        help_text=_("Section title"),
    )
    description = blocks.CharBlock(
        max_length=150,
        required=False,
        label=_("Section Description"),
    )

    items = blocks.ListBlock(
        blocks.CharBlock(
            max_length=150,
            label=_("Item"),
        ),
        label=_("Items"),
    )
    image = ImageChooserBlock()

    class Meta:
        template = "blocks/info_block.html"
        icon = "placeholder"
        label = _("Title, Text and Image")


class FeatureBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        max_length=100,
        label=_("Title"),
    )
    icon = IconChooserBlock(label=_("Icon"))
    description = blocks.CharBlock(
        max_length=150,
        label=_("Description"),
    )


class ActionCardBlock(blocks.StructBlock):
    """Action card for 'What You Can Do' section on homepage."""

    title = blocks.CharBlock(
        max_length=100,
        label=_("Title"),
        help_text=_("e.g., 'Monitor Flooding', 'Track Rainfall'"),
    )
    icon = IconChooserBlock(
        required=False,
        label=_("Icon"),
        help_text=_("Select an icon for this action (optional if using image)"),
    )
    image = ImageChooserBlock(
        required=False,
        label=_("Image"),
        help_text=_("Upload an image for this action (optional if using icon)"),
    )
    description = blocks.CharBlock(
        max_length=200,
        label=_("Description"),
        help_text=_("Brief description of what users can do"),
    )
    link_url = blocks.CharBlock(
        max_length=500,
        label=_("Link URL"),
        help_text=_("URL to link to (e.g., '/mapviewer/', '/reports/')"),
    )
    link_text = blocks.CharBlock(
        max_length=50,
        default="Learn More",
        label=_("Link Text"),
        help_text=_("Text for the action link (e.g., 'Open Map', 'View Reports')"),
    )

    class Meta:
        icon = "link"
        label = _("Action Card")


class LinkBlock(blocks.StructBlock):
    """A reusable block for a single link."""

    name = blocks.CharBlock(
        max_length=100,
        label=_("Link Text"),
        help_text=_("The text displayed for the link"),
    )
    url = blocks.CharBlock(
        # CharBlock to allow having relative urls e.g., '/about', '/home'
        max_length=500,
        label=_("URL"),
        help_text=_("The URL this link points to (e.g., '/' for home, '/about/', or 'https://example.com')"),
    )
    open_in_new_tab = blocks.BooleanBlock(
        required=False,
        default=False,
        label=_("Open in new tab"),
        help_text=_("Check to open this link in a new browser tab"),
    )

    class Meta:
        icon = "link"
        label = _("Link")


class LinkGroupBlock(blocks.StructBlock):
    """A block representing a group of links with a title.(can be used for footers or dropdowns)"""

    title = blocks.CharBlock(
        max_length=100,
        label=_("Title"),
        help_text=_("The heading for this group of links"),
    )
    links = blocks.ListBlock(
        LinkBlock(),
        label=_("Links"),
        help_text=_("Add links for this section"),
    )

    class Meta:
        icon = "list-ul"
        label = _("Link Group")


class SocialLinkBlock(blocks.StructBlock):
    """Social media link with name, icon, and URL."""

    name = blocks.CharBlock(
        max_length=50,
        label=_("Platform Name"),
        help_text=_("Name of the social media platform (e.g., Facebook, Twitter)"),
    )
    icon = ImageChooserBlock(
        label=_("Icon"),
        help_text=_("Select an icon for this social media platform"),
    )
    url = blocks.URLBlock(
        label=_("Profile URL"),
        help_text=_("Full URL to your social media profile"),
    )

    class Meta:
        icon = "user"
        label = _("Social Link")


class LogoItemBlock(blocks.StructBlock):
    """Reusable block for displaying an item with image/logo and name."""

    name = blocks.CharBlock(max_length=200, label=_("Name"))
    description = blocks.TextBlock(
        required=False,
        label=_("Description"),
        help_text=_("Brief description of the partner organization"),
    )
    image = ImageChooserBlock(label=_("Image/Logo/Banner"))
    url = blocks.CharBlock(max_length=500, required=False, label=_("Link URL"))
    show_on_homepage = blocks.BooleanBlock(
        required=False,
        default=False,
        label=_("Major Partner (Show on Homepage)"),
        help_text=_("Enable this to feature the partner in the homepage partner strip"),
    )

    class Meta:
        icon = "image"
        label = _("Partner")


class CountryBlock(blocks.StructBlock):
    """Block for selecting a country - flag auto-loads from CDN."""
    from django_countries import countries

    country = blocks.ChoiceBlock(
        choices=list(countries),
        label=_("Country"),
        help_text=_("Select a country - flag will load automatically"),
    )
    url = blocks.CharBlock(max_length=500, required=False, label=_("Link URL"))

    class Meta:
        icon = "globe"
        label = _("Country")


# =============================================================================
# HOMEPAGE SECTION BLOCKS - Flexible homepage layout
# =============================================================================

class HeroBannerBlock(blocks.StructBlock):
    """Full-width hero banner section with background image."""

    background_image = ImageChooserBlock(
        label=_("Background Image"),
        help_text=_("High-quality background image for the hero section"),
    )
    title = blocks.CharBlock(
        max_length=200,
        label=_("Title"),
        help_text=_("Main headline (e.g., 'East Africa Flood Watch')"),
    )
    subtitle = blocks.TextBlock(
        required=False,
        label=_("Subtitle"),
        help_text=_("Supporting text below the title"),
    )
    cta_text = blocks.CharBlock(
        max_length=50,
        required=False,
        default="Explore Map",
        label=_("Button Text"),
    )
    cta_url = blocks.CharBlock(
        max_length=500,
        required=False,
        default="/mapviewer/",
        label=_("Button URL"),
    )
    overlay_opacity = blocks.IntegerBlock(
        default=40,
        label=_("Overlay Opacity (%)"),
        help_text=_("Dark overlay opacity (0-100) to improve text readability"),
    )
    min_height = blocks.IntegerBlock(
        default=500,
        label=_("Minimum Height (px)"),
    )
    text_alignment = blocks.ChoiceBlock(
        choices=[
            ('left', _('Left')),
            ('center', _('Center')),
            ('right', _('Right')),
        ],
        default='left',
        label=_("Text Alignment"),
    )

    class Meta:
        template = "blocks/hero_banner_block.html"
        icon = "image"
        label = _("Hero Banner")


class FloodMapWidgetBlock(blocks.StructBlock):
    """Flood monitoring map widget section."""

    section_title = blocks.CharBlock(
        max_length=200,
        default="Latest Situation of Flood Conditions",
        label=_("Section Title"),
    )
    show_date_in_title = blocks.BooleanBlock(
        default=True,
        required=False,
        label=_("Show Date in Title"),
    )
    show_map = blocks.BooleanBlock(
        default=True,
        required=False,
        label=_("Show Map"),
    )
    show_country_cards = blocks.BooleanBlock(
        default=True,
        required=False,
        label=_("Show Country Cards"),
    )
    country_cards_title = blocks.CharBlock(
        max_length=200,
        default="Regional Flood Situation",
        label=_("Country Cards Title"),
    )
    point_filter = blocks.ChoiceBlock(
        choices=[
            ('all', _('All Points')),
            ('active', _('Active Points Only (Warning+)')),
            ('alarm', _('Alarm and Above')),
            ('emergency', _('Emergency Only')),
        ],
        default='all',
        label=_("Point Filter"),
    )
    map_height = blocks.IntegerBlock(
        default=480,
        label=_("Map Height (px)"),
    )

    class Meta:
        template = "blocks/flood_map_widget_block.html"
        icon = "site"
        label = _("Flood Map Widget")


class InfoSectionBlock(blocks.StructBlock):
    """Information/About section with text and optional image."""

    title = blocks.CharBlock(
        max_length=200,
        label=_("Section Title"),
    )
    content = blocks.RichTextBlock(
        features=['bold', 'italic', 'ol', 'ul', 'link', 'h3', 'h4'],
        label=_("Content"),
    )
    image = ImageChooserBlock(
        required=False,
        label=_("Image"),
    )
    image_position = blocks.ChoiceBlock(
        choices=[
            ('left', _('Image Left')),
            ('right', _('Image Right')),
            ('top', _('Image Top')),
            ('bottom', _('Image Bottom')),
        ],
        default='right',
        label=_("Image Position"),
    )
    background_color = blocks.ChoiceBlock(
        choices=[
            ('white', _('White')),
            ('light', _('Light Gray')),
            ('primary', _('Primary Color')),
        ],
        default='white',
        label=_("Background Color"),
    )

    class Meta:
        template = "blocks/info_section_block.html"
        icon = "doc-full"
        label = _("Info Section")


class FeatureCardBlock(blocks.StructBlock):
    """Single feature card for the features grid."""

    title = blocks.CharBlock(
        max_length=100,
        label=_("Title"),
    )
    description = blocks.TextBlock(
        label=_("Description"),
    )
    icon = ImageChooserBlock(
        required=False,
        label=_("Icon/Image"),
    )
    link_url = blocks.CharBlock(
        max_length=500,
        required=False,
        label=_("Link URL"),
    )
    link_text = blocks.CharBlock(
        max_length=50,
        required=False,
        default="Learn More",
        label=_("Link Text"),
    )


class FeatureCardsBlock(blocks.StructBlock):
    """Grid of feature cards."""

    title = blocks.CharBlock(
        max_length=200,
        required=False,
        label=_("Section Title"),
    )
    subtitle = blocks.TextBlock(
        required=False,
        label=_("Section Subtitle"),
    )
    cards = blocks.ListBlock(
        FeatureCardBlock(),
        label=_("Feature Cards"),
        min_num=1,
        max_num=6,
    )
    columns = blocks.ChoiceBlock(
        choices=[
            ('2', _('2 Columns')),
            ('3', _('3 Columns')),
            ('4', _('4 Columns')),
        ],
        default='3',
        label=_("Number of Columns"),
    )
    background_color = blocks.ChoiceBlock(
        choices=[
            ('white', _('White')),
            ('light', _('Light Gray')),
        ],
        default='light',
        label=_("Background Color"),
    )

    class Meta:
        template = "blocks/feature_cards_block.html"
        icon = "grip"
        label = _("Feature Cards")


class CTABannerBlock(blocks.StructBlock):
    """Call-to-action banner section."""

    title = blocks.CharBlock(
        max_length=200,
        label=_("Title"),
    )
    description = blocks.TextBlock(
        required=False,
        label=_("Description"),
    )
    button_text = blocks.CharBlock(
        max_length=50,
        default="Get Started",
        label=_("Button Text"),
    )
    button_url = blocks.CharBlock(
        max_length=500,
        label=_("Button URL"),
    )
    background_color = blocks.ChoiceBlock(
        choices=[
            ('primary', _('Primary Color')),
            ('secondary', _('Secondary Color')),
            ('dark', _('Dark')),
        ],
        default='primary',
        label=_("Background Color"),
    )

    class Meta:
        template = "blocks/cta_banner_block.html"
        icon = "pick"
        label = _("CTA Banner")


class PartnersBlock(blocks.StructBlock):
    """Partners/logos section."""

    title = blocks.CharBlock(
        max_length=200,
        default="Our Partners",
        required=False,
        label=_("Section Title"),
    )
    partners = blocks.ListBlock(
        LogoItemBlock(),
        label=_("Partners"),
    )

    class Meta:
        template = "blocks/partners_block.html"
        icon = "group"
        label = _("Partners")
