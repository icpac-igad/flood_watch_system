from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class ContactInfoBlock(blocks.StructBlock):
    """A single contact info entry with a Font Awesome icon, title, and rich text content."""

    icon = blocks.CharBlock(
        max_length=100,
        label=_("Icon"),
        help_text=_("Font Awesome class, e.g. 'fas fa-location-dot' or 'fas fa-envelope'"),
    )
    title = blocks.CharBlock(
        max_length=100,
        label=_("Title"),
    )
    content = blocks.RichTextBlock(
        features=["bold", "italic", "link"],
        label=_("Content"),
        help_text=_("Use links for email addresses (mailto:) and URLs."),
    )

    class Meta:
        icon = "list-ul"
        label = _("Contact Info Block")
