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
