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
        required=False,
        label=_("Description"),
    )


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


IGAD_COUNTRY_CHOICES = [
    ("bi", _("Burundi")),
    ("dj", _("Djibouti")),
    ("er", _("Eritrea")),
    ("et", _("Ethiopia")),
    ("ke", _("Kenya")),
    ("rw", _("Rwanda")),
    ("so", _("Somalia")),
    ("ss", _("South Sudan")),
    ("sd", _("Sudan")),
    ("tz", _("Tanzania")),
    ("ug", _("Uganda")),
]


class MemberStateBlock(blocks.StructBlock):
    """A block for displaying a member state with its flag (auto-populated from country code)."""

    country_code = blocks.ChoiceBlock(
        choices=IGAD_COUNTRY_CHOICES,
        label=_("Country"),
        help_text=_("Select the member state — flag will load automatically"),
    )
    name = blocks.CharBlock(
        max_length=100,
        label=_("Display Name"),
        required=False,
        help_text=_("Override display name (leave blank to use country name)"),
    )
    is_project_country = blocks.BooleanBlock(
        required=False,
        default=False,
        label=_("Project Country"),
        help_text=_("Tick if this country is part of the current project (e.g. WHCA)"),
    )

    class Meta:
        icon = "globe"
        label = _("Member State")


class CTAButtonBlock(blocks.StructBlock):
    """A call-to-action button with title and URL."""

    title = blocks.CharBlock(
        max_length=200,
        label=_("Button Title"),
        help_text=_("Text to display on the button"),
    )
    url = blocks.CharBlock(
        max_length=500,
        label=_("URL"),
        help_text=_("URL to link to. Can be relative (e.g. '/mapviewer/') or full (e.g. 'https://example.com')"),
    )

    class Meta:
        icon = "link"
        label = _("CTA Button")


class PartnerBlock(blocks.StructBlock):
    name = blocks.CharBlock(max_length=100, label=_("Partner Name"))
    logo = ImageChooserBlock(required=False, label=_("Partner Logo"))
    url = blocks.URLBlock(required=False, label=_("Website URL"))

    class Meta:
        icon = "group"
        label = _("Partner")


class PartnerGroupBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=100, label=_("Group Title"))
    icon = blocks.CharBlock(max_length=50, required=False, default="fa-handshake", label=_("Icon CSS class"))
    description = blocks.CharBlock(max_length=255, required=False, label=_("Description"))
    partners = blocks.ListBlock(PartnerBlock(), label=_("Partners"))

    class Meta:
        icon = "group"
        label = _("Partner Group")


class SocialLinkBlock(blocks.StructBlock):
    """Social media link with name, icon, and URL."""

    name = blocks.CharBlock(
        max_length=50,
        label=_("Platform Name"),
        help_text=_("Name of the social media platform (e.g., Facebook, Twitter)"),
    )
    icon = blocks.CharBlock(
        max_length=100,
        label=_("Icon"),
        help_text=_("Font Awesome (v4.7.0) class, e.g. 'fab fa-facebook' or 'fab fa-x-twitter'"),
    )
    url = blocks.URLBlock(
        label=_("Profile URL"),
        help_text=_("Full URL to your social media profile"),
    )

    class Meta:
        icon = "user"
        label = _("Social Link")
