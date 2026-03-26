from django.core.cache import cache
from .models import SiteTheme, Navbar, Footer, LanguageSettings


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
    try:
        language_settings = LanguageSettings.objects.prefetch_related("languages").first()
    except Exception:
        language_settings = None

    if language_settings and language_settings.multilanguage_enabled:
        languages = language_settings.languages.all()
        default_language = languages.filter(is_default=True).first()
    else:
        languages = []
        default_language = None

    return {
        "language_settings": language_settings,
        "languages": languages,
        "default_language": default_language,
    }


def footer_context(request):
    footer = Footer.objects.live().first()
    return {"footer": footer}
