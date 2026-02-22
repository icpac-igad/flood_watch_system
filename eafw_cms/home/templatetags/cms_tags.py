import logging
import re

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


def _stream_items(stream_value):
    if not stream_value:
        return []
    try:
        return list(stream_value)
    except TypeError:
        return []


def _block_value(block):
    return getattr(block, "value", None)


def _country_code_from_block(block):
    value = _block_value(block)
    if value is None:
        return ""
    if hasattr(value, "get"):
        return (value.get("country") or "").strip().upper()
    return str(getattr(value, "country", "") or "").strip().upper()


def _normalize_partner_name(raw):
    text = str(raw or "").strip().lower()
    text = text.replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", text)


def _partner_key_from_block(block):
    value = _block_value(block)
    if value is None:
        return ""

    if hasattr(value, "get"):
        name = value.get("name") or ""
        image = value.get("image")
        url = value.get("url") or ""
    else:
        name = getattr(value, "name", "") or ""
        image = getattr(value, "image", None)
        url = getattr(value, "url", "") or ""

    normalized_name = _normalize_partner_name(name)
    if normalized_name:
        return f"name:{normalized_name}"

    image_id = str(getattr(image, "id", "") or "").strip()
    if image_id:
        return f"image:{image_id}"

    normalized_url = str(url).strip().lower()
    if normalized_url:
        return f"url:{normalized_url}"

    return ""


@register.filter
def unique_member_countries(stream_value):
    """
    Return member country blocks with duplicates removed by ISO2 code.
    Keeps first occurrence order.
    """
    items = _stream_items(stream_value)
    if not items:
        return []

    seen = set()
    unique_items = []
    for block in items:
        code = _country_code_from_block(block)
        if not code or code in seen:
            continue
        seen.add(code)
        unique_items.append(block)

    return unique_items


@register.filter
def unique_partners(stream_value):
    """
    Return partner blocks with duplicates removed by image/name/url key.
    Keeps first occurrence order.
    """
    items = _stream_items(stream_value)
    if not items:
        return []

    seen = set()
    unique_items = []
    for block in items:
        key = _partner_key_from_block(block)
        if not key or key in seen:
            continue
        seen.add(key)
        unique_items.append(block)

    return unique_items


@register.filter
def homepage_partners(stream_value):
    """
    Return partners marked as `show_on_homepage`.
    If none are marked, return all provided items to avoid an empty homepage strip.
    """
    items = _stream_items(stream_value)
    if not items:
        return []

    featured_items = []
    for block in items:
        value = _block_value(block)
        if value is None:
            continue

        if hasattr(value, "get"):
            show_on_homepage = value.get("show_on_homepage")
        else:
            show_on_homepage = getattr(value, "show_on_homepage", False)

        if bool(show_on_homepage):
            featured_items.append(block)

    return featured_items or items


@register.simple_tag
def safe_image_url(image, spec="original"):
    """
    Resolve a Wagtail image URL without hard-failing template rendering.
    Returns an empty string when the image/rendition cannot be resolved.
    """
    if not image:
        return ""

    try:
        mode = str(spec or "original").strip().lower()
        if mode in {"original", "source", "full"}:
            image_file = getattr(image, "file", None)
            return image_file.url if image_file else ""
        return image.get_rendition(spec).url
    except Exception as exc:
        logger.warning(
            "Failed to resolve image URL (image_id=%s, spec=%s): %s",
            getattr(image, "id", "unknown"),
            spec,
            exc,
        )
        return ""
