from asgiref.sync import async_to_sync
from django_nextjs.render import render_nextjs_page
from django.utils.translation import get_language

from home.models import Navbar, LanguageSettings
from home.context_processors import theme_context


def _get_common_context(request):
    navbar = Navbar.objects.live().first()
    try:
        lang_settings = LanguageSettings.objects.first()
        cms_languages = lang_settings.get_enabled_languages() if lang_settings else [("en", "English")]
    except Exception:
        cms_languages = [("en", "English")]
    theme = theme_context(request).get("theme", {})
    return {
        "navbar": navbar,
        "cms_languages": cms_languages,
        "current_language": get_language() or "en",
        "theme": theme,
    }


def storylines_hub_view(request):
    """Storylines hub page — lists all published storylines."""
    context = _get_common_context(request)
    return async_to_sync(render_nextjs_page)(
        request, "django_nextjs/storylines.html", context, allow_redirects=True
    )


def storyline_detail_view(request, slug):
    """Individual storyline viewer with scrollytelling."""
    context = _get_common_context(request)
    return async_to_sync(render_nextjs_page)(
        request, "django_nextjs/storylines.html", context, allow_redirects=True
    )
