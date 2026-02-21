from asgiref.sync import async_to_sync
from django_nextjs.render import render_nextjs_page
from django.shortcuts import render
from django.utils.translation import get_language
from wagtailiconchooser.utils import get_svg_sprite_for_icons

from geomanager.models import Category
from geomanager.models.vector_file import get_legend_icons
from home.models import Navbar, Footer, LanguageSettings
from home.context_processors import theme_context


def map_view(request, location_type=None, adm0=None, adm1=None, adm2=None):
    """Custom mapviewer view that includes navbar context"""
    # get svg sprite for categories and legend icons
    category_icons = [category.icon for category in Category.objects.all()]
    legend_icons = get_legend_icons()
    icons = [*category_icons, *legend_icons]
    svg_sprite = get_svg_sprite_for_icons(icons)

    # Get navbar from CMS
    navbar = Navbar.objects.live().first()

    # Get enabled languages from CMS
    try:
        lang_settings = LanguageSettings.objects.first()
        cms_languages = lang_settings.get_enabled_languages() if lang_settings else [("en", "English")]
    except Exception:
        cms_languages = [("en", "English")]

    # Get theme context
    theme = theme_context(request).get("theme", {})

    context = {
        "svg_sprite": svg_sprite,
        "navbar": navbar,
        "cms_languages": cms_languages,
        "current_language": get_language() or "en",
        "theme": theme,
    }

    return async_to_sync(render_nextjs_page)(
        request, "django_nextjs/mapviewer.html", context, allow_redirects=True
    )


def flood_analysis_view(request):
    """Flood analysis report view that renders the Next.js flood-analysis page"""
    # Get navbar from CMS
    navbar = Navbar.objects.live().first()

    # Get enabled languages from CMS
    try:
        lang_settings = LanguageSettings.objects.first()
        cms_languages = lang_settings.get_enabled_languages() if lang_settings else [("en", "English")]
    except Exception:
        cms_languages = [("en", "English")]

    # Get theme context
    theme = theme_context(request).get("theme", {})

    context = {
        "navbar": navbar,
        "cms_languages": cms_languages,
        "current_language": get_language() or "en",
        "theme": theme,
    }

    return async_to_sync(render_nextjs_page)(
        request, "django_nextjs/flood-analysis.html", context, allow_redirects=True
    )


def partners_view(request):
    """Partners page view - displays partners and member countries from CMS Footer"""
    # Get navbar and footer from CMS
    navbar = Navbar.objects.live().first()
    footer = Footer.objects.live().first()

    # Get enabled languages from CMS
    try:
        lang_settings = LanguageSettings.objects.first()
        cms_languages = lang_settings.get_enabled_languages() if lang_settings else [("en", "English")]
    except Exception:
        cms_languages = [("en", "English")]

    # Get theme context
    theme = theme_context(request).get("theme", {})

    context = {
        "navbar": navbar,
        "footer": footer,
        "cms_languages": cms_languages,
        "current_language": get_language() or "en",
        "theme": theme,
        "page_title": footer.partners_page_title if footer else "Our Partners",
    }

    return render(request, "home/partners_page.html", context)
