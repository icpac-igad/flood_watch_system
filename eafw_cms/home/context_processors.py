from django.core.cache import cache
from django.utils.translation import get_language
from django.db import connection
from .models import SiteTheme, Navbar, LanguageSettings


def theme_context(request):
    theme = cache.get("active_theme")
    if not theme:
        try:
            theme = SiteTheme.objects.get(is_active=True)
            cache.set("active_theme", theme, 60 * 60 * 24)  # Cache for 24 hours
        except SiteTheme.DoesNotExist:
            # Fallback to default colors
            theme = {
                "primary_color": "#034930",
                "secondary_color": "#198754",
                "accent_color": "#fbc02d",
                "primary_text_color": "#ffffff",
                "secondary_text_color": "#333333",
                "background_color": "#ffffff",
            }
    return {"theme": theme}


def navbar_context(request):
    navbar = Navbar.objects.live().first()
    return {"navbar": navbar}


def language_context(request):
    """Load enabled languages from CMS settings."""
    enabled_languages = cache.get("enabled_languages")

    if enabled_languages is None:
        try:
            # Query directly from database
            lang_settings = LanguageSettings.objects.first()
            if lang_settings:
                enabled_languages = lang_settings.get_enabled_languages()
            else:
                enabled_languages = [("en", "English")]
            cache.set("enabled_languages", enabled_languages, 60 * 60)  # Cache for 1 hour
        except Exception:
            # Fallback to English only
            enabled_languages = [("en", "English")]

    return {
        "cms_languages": enabled_languages,
        "current_language": get_language() or "en",
    }
