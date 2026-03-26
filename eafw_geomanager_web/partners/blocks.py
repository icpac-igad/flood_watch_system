from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class PartnerBlock(blocks.StructBlock):
    """A block for displaying partner information."""

    name = blocks.CharBlock(
        max_length=200,
        required=False,
        label=_("Project Name"),
        help_text=_("Name of the Project"),
    )
    logo = ImageChooserBlock(
        required=False,
        label=_("Partner Logo"),
        help_text=_("Logo of the partner organization"),
    )
    description = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link"],
        label=_("Description"),
        help_text=_("Brief description of the Project. You can add links within the text."),
    )
    website_url = blocks.URLBlock(
        required=False,
        label=_("Website URL"),
        help_text=_("Partner's website URL"),
    )

    class Meta:
        icon = "group"
        label = _("Partner")
