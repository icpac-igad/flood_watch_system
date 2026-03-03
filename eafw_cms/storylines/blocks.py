from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock


class ReferenceBlock(blocks.StructBlock):
    """External reference link (ReliefWeb, news articles, etc.)."""

    title = blocks.CharBlock(
        max_length=300,
        label=_("Title"),
        help_text=_("Reference title or description"),
    )
    url = blocks.URLBlock(
        label=_("URL"),
        help_text=_("Link to the source"),
    )

    class Meta:
        icon = "link-external"
        label = _("Reference")


class MediaBlock(blocks.StreamBlock):
    """Flexible media content for a chapter."""

    image = ImageChooserBlock(label=_("Uploaded Image"))
    external_image = blocks.StructBlock(
        [
            ("url", blocks.URLBlock(label=_("Image URL"))),
            ("alt", blocks.CharBlock(max_length=200, label=_("Alt Text"))),
            ("caption", blocks.CharBlock(max_length=500, required=False, label=_("Caption"))),
        ],
        icon="image",
        label=_("External Image"),
    )
    embed = blocks.StructBlock(
        [
            ("url", blocks.URLBlock(label=_("Embed URL"))),
            ("title", blocks.CharBlock(max_length=200, required=False, label=_("Title"))),
            ("height", blocks.IntegerBlock(default=400, label=_("Height (px)"))),
        ],
        icon="media",
        label=_("Embed (iframe)"),
    )
    external_video = blocks.StructBlock(
        [
            ("url", blocks.URLBlock(label=_("Video URL"))),
            ("title", blocks.CharBlock(max_length=200, required=False, label=_("Title"))),
            ("poster_url", blocks.URLBlock(required=False, label=_("Poster Image URL"))),
            ("caption", blocks.CharBlock(max_length=500, required=False, label=_("Caption"))),
            ("autoplay", blocks.BooleanBlock(required=False, default=False, label=_("Autoplay"))),
            ("muted", blocks.BooleanBlock(required=False, default=True, label=_("Muted"))),
            ("loop", blocks.BooleanBlock(required=False, default=False, label=_("Loop"))),
        ],
        icon="media",
        label=_("External Video"),
    )
    uploaded_video = blocks.StructBlock(
        [
            ("file", DocumentChooserBlock(label=_("Video File"))),
            ("title", blocks.CharBlock(max_length=200, required=False, label=_("Title"))),
            ("poster_url", blocks.URLBlock(required=False, label=_("Poster Image URL"))),
            ("caption", blocks.CharBlock(max_length=500, required=False, label=_("Caption"))),
            ("autoplay", blocks.BooleanBlock(required=False, default=False, label=_("Autoplay"))),
            ("muted", blocks.BooleanBlock(required=False, default=True, label=_("Muted"))),
            ("loop", blocks.BooleanBlock(required=False, default=False, label=_("Loop"))),
        ],
        icon="media",
        label=_("Uploaded Video"),
    )

    class Meta:
        icon = "image"
        label = _("Media")


class MapOverlayBlock(blocks.StructBlock):
    """GeoJSON overlay styling for chapter map scenes."""

    label = blocks.CharBlock(
        max_length=120,
        required=False,
        label=_("Label"),
        help_text=_("Optional short name shown in the chapter card"),
    )
    url = blocks.URLBlock(
        label=_("GeoJSON URL"),
        help_text=_("Public URL to a GeoJSON file for this chapter overlay"),
    )
    layer_type = blocks.ChoiceBlock(
        choices=[
            ("fill", _("Fill Polygon")),
            ("line", _("Line")),
            ("circle", _("Point Circles")),
        ],
        default="fill",
        label=_("Layer Type"),
    )
    color = blocks.CharBlock(
        max_length=32,
        required=False,
        default="#38bdf8",
        label=_("Color"),
        help_text=_("CSS color (for example #38bdf8 or rgba(56,189,248,1))"),
    )
    opacity = blocks.FloatBlock(
        required=False,
        default=0.45,
        min_value=0,
        max_value=1,
        label=_("Opacity"),
    )
    line_width = blocks.FloatBlock(
        required=False,
        default=2,
        min_value=0,
        label=_("Line Width"),
    )
    point_radius = blocks.FloatBlock(
        required=False,
        default=5,
        min_value=0,
        label=_("Point Radius"),
    )

    class Meta:
        icon = "site"
        label = _("Map Overlay")


class MapStateBlock(blocks.StructBlock):
    """Map camera state for a chapter."""

    center_lon = blocks.FloatBlock(
        label=_("Center Longitude"),
        help_text=_("Map center longitude (e.g., 38.5)"),
    )
    center_lat = blocks.FloatBlock(
        label=_("Center Latitude"),
        help_text=_("Map center latitude (e.g., 5.0)"),
    )
    zoom = blocks.FloatBlock(
        default=5,
        label=_("Zoom Level"),
        help_text=_("Map zoom (0-18)"),
    )
    bearing = blocks.FloatBlock(
        default=0,
        required=False,
        label=_("Bearing"),
        help_text=_("Map rotation in degrees (0-360)"),
    )
    pitch = blocks.FloatBlock(
        default=0,
        required=False,
        label=_("Pitch"),
        help_text=_("Map tilt in degrees (0-60)"),
    )

    class Meta:
        icon = "site"
        label = _("Map State")


class ChapterBlock(blocks.StructBlock):
    """A single chapter/step in a storyline."""

    title = blocks.CharBlock(
        max_length=200,
        label=_("Chapter Title"),
    )
    prose = blocks.RichTextBlock(
        features=["bold", "italic", "ol", "ul", "link", "h3", "h4", "blockquote"],
        label=_("Narrative Text"),
        help_text=_("The story content for this chapter"),
    )
    map_state = MapStateBlock(
        required=False,
        label=_("Map View"),
        help_text=_("Where the map should fly to for this chapter"),
    )
    map_overlays = blocks.ListBlock(
        MapOverlayBlock(),
        required=False,
        label=_("Map Overlays"),
        help_text=_("GeoJSON flood layers to render when this chapter is active"),
    )
    transition = blocks.ChoiceBlock(
        choices=[
            ("fly", _("Fly To (animated)")),
            ("jump", _("Jump To (instant)")),
            ("ease", _("Ease To (slow pan)")),
        ],
        default="fly",
        label=_("Map Transition"),
    )
    date_start = blocks.DateBlock(
        required=False,
        label=_("Event Start Date"),
        help_text=_("For timeline playback — start of date range"),
    )
    date_end = blocks.DateBlock(
        required=False,
        label=_("Event End Date"),
        help_text=_("For timeline playback — end of date range"),
    )
    media = MediaBlock(
        required=False,
        label=_("Media"),
        help_text=_("Images, embeds, or external media for this chapter"),
    )
    references = blocks.ListBlock(
        ReferenceBlock(),
        required=False,
        label=_("References"),
        help_text=_("Source links for this chapter"),
    )

    class Meta:
        icon = "doc-full"
        label = _("Chapter")


class CountryEventBlock(blocks.StructBlock):
    """A country-specific event entry within a storyline."""

    from django_countries import countries

    country = blocks.ChoiceBlock(
        choices=list(countries),
        label=_("Country"),
    )
    event_period = blocks.CharBlock(
        max_length=50,
        label=_("Event Period"),
        help_text=_("e.g., 'October-December 2023' or '20231001-20231231'"),
    )
    emdat_codes = blocks.CharBlock(
        max_length=200,
        required=False,
        label=_("EM-DAT Codes"),
        help_text=_("Comma-separated EM-DAT disaster codes (e.g., '2024-0150-KEN')"),
    )

    class Meta:
        icon = "globe"
        label = _("Country Event")
