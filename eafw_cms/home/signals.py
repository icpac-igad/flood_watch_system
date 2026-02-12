from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from wagtailcache.cache import clear_cache as clear_wagtail_cache

from .models import EnabledLanguage, LanguageSettings, SiteTheme


def _clear_language_related_caches():
    # Used by the navbar template and Google Translate config.
    cache.delete("enabled_languages")

    # Public pages are cached by wagtail-cache; flush so language changes show immediately.
    try:
        clear_wagtail_cache()
    except Exception:
        pass


@receiver(post_save, sender=SiteTheme)
def clear_theme_cache_on_save(sender, instance, **kwargs):
    cache.delete("active_theme")
    print("Theme cache cleared on save")


@receiver(post_delete, sender=SiteTheme)
def clear_theme_cache_on_delete(sender, instance, **kwargs):
    cache.delete("active_theme")
    print("Theme cache cleared on delete")


@receiver(post_save, sender=LanguageSettings)
def clear_language_cache_on_save(sender, instance, **kwargs):
    _clear_language_related_caches()
    print("Language cache cleared on save")


@receiver(post_delete, sender=LanguageSettings)
def clear_language_cache_on_delete(sender, instance, **kwargs):
    _clear_language_related_caches()
    print("Language cache cleared on delete")


@receiver(post_save, sender=EnabledLanguage)
def clear_enabled_language_cache_on_save(sender, instance, **kwargs):
    # Editing LanguageSettings (InlinePanel) also saves child rows; keep the context processor cache in sync.
    cache.delete("enabled_languages")


@receiver(post_delete, sender=EnabledLanguage)
def clear_enabled_language_cache_on_delete(sender, instance, **kwargs):
    cache.delete("enabled_languages")
