from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import SiteTheme


@receiver(post_save, sender=SiteTheme)
def clear_theme_cache_on_save(sender, instance, **kwargs):
    cache.delete("active_theme")
    print("Theme cache cleared on save")


@receiver(post_delete, sender=SiteTheme)
def clear_theme_cache_on_delete(sender, instance, **kwargs):
    cache.delete("active_theme")
    print("Theme cache cleared on delete")
