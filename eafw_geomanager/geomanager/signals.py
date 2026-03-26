import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from geomanager.models import Dataset, WatcherConfig

logger = logging.getLogger("geomanager.signals")


def _submit_to_scheduler(dataset_slug: str, triggered_by: str = "cms"):
    """Submit a dataset update to the WatcherScheduler (non-blocking)."""
    try:
        from geomanager.tasks.periodic import WatcherScheduler

        WatcherScheduler.get_instance().submit(dataset_slug, triggered_by=triggered_by)
    except Exception as e:
        logger.error(f"Failed to submit watcher for '{dataset_slug}': {e}", exc_info=True)


@receiver(post_save, sender=Dataset)
def dataset_saved_trigger_watcher(sender, instance, created, update_fields, **kwargs):
    """
    Trigger a watcher update whenever a dataset is saved with a valid watcher_config.
    Uses triggered_by="cms" so the update runs regardless of auto_update_frequency.
    QuerySet.update() calls inside the watcher bypass post_save signals entirely,
    so there is no cascade risk.
    """
    if not instance.dataset_slug:
        return

    if not instance.watcher_config or not instance.watcher_config.api_url:
        return

    _submit_to_scheduler(instance.dataset_slug, triggered_by="cms")


@receiver(post_save, sender=WatcherConfig)
def watcher_config_saved_trigger_updates(sender, instance, created, **kwargs):
    """When a WatcherConfig is saved, trigger updates for all datasets using it."""
    if not instance.api_url:
        return

    # Single query: fetch all slugs at once instead of exists() + count() + iterate
    dataset_slugs = list(
        instance.datasets.filter(dataset_slug__isnull=False)
        .exclude(dataset_slug="")
        .values_list("dataset_slug", flat=True)
    )

    if not dataset_slugs:
        logger.info(f"WatcherConfig '{instance.title}' saved but no datasets are using it")
        return

    logger.info(f"WatcherConfig '{instance.title}' saved, triggering {len(dataset_slugs)} dataset(s)")

    for slug in dataset_slugs:
        _submit_to_scheduler(slug, triggered_by="cms")
