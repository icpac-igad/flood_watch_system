import logging

from django import template
from django.conf import settings
from django_countries import countries

logger = logging.getLogger(__name__)
register = template.Library()


@register.filter
def django_settings(value):
    return getattr(settings, value, None)


@register.filter
def country_name(code):
    """Get country name from country code."""
    return countries.name(code) if code else ""


@register.filter
def sort_member_countries(stream_value):
    """
    Sort Footer.member_countries alphabetically by country name.

    Input is typically a Wagtail StreamValue containing StructBlock items with
    a "country" ISO2 code.
    """
    if not stream_value:
        return []

    try:
        items = list(stream_value)
    except TypeError:
        return stream_value

    def _code_from_block(block):
        try:
            value = getattr(block, "value", None)
            if value is None:
                return ""
            if hasattr(value, "get"):
                return value.get("country") or ""
            return getattr(value, "country", "") or ""
        except Exception:
            return ""

    def _sort_key(block):
        code = _code_from_block(block)
        name = countries.name(code) if code else ""
        return (str(name).casefold(), str(code).casefold())

    return sorted(items, key=_sort_key)
