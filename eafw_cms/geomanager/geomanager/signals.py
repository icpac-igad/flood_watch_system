import logging
import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
from geomanager.models import Dataset, WatcherConfig

logger = logging.getLogger("geomanager.signals")


def trigger_dataset_watcher_async(dataset_slug):
    """Trigger dataset watcher in a background thread to avoid blocking the save operation."""
    from geomanager.tasks.watchers import update_dataset_date

    def run_watcher():
        try:
            update_dataset_date(dataset_slug, triggered_by="cms")
        except Exception as e:
            logger.error(f"Error in CMS-triggered watcher for '{dataset_slug}': {str(e)}", exc_info=True)

    thread = threading.Thread(target=run_watcher, daemon=True)
    thread.start()


@receiver(post_save, sender=Dataset)
def dataset_saved_trigger_watcher(sender, instance, created, **kwargs):
    # Need dataset_slug for the watcher to work
    if not instance.dataset_slug:
        logger.warning(f"Dataset '{instance.title}' has no dataset_slug")
        return

    # Simple check: if watcher_config is set and has an api_url, trigger the watcher
    if not instance.watcher_config:
        return

    if not instance.watcher_config.api_url:
        return

    # Trigger watcher asynchronously
    trigger_dataset_watcher_async(instance.dataset_slug)


@receiver(post_save, sender=WatcherConfig)
def watcher_config_saved_trigger_updates(sender, instance, created, **kwargs):
    """When a WatcherConfig is saved, trigger updates for all datasets using it."""
    if not instance.api_url:
        return

    # Get all datasets using this watcher config
    datasets = instance.datasets.all()

    if not datasets.exists():
        logger.info(f"WatcherConfig '{instance.title}' saved but no datasets are using it")
        return

    logger.info(f"WatcherConfig '{instance.title}' saved, triggering updates for {datasets.count()} dataset(s)")

    # Trigger watcher for each dataset
    for dataset in datasets:
        if dataset.dataset_slug:
            trigger_dataset_watcher_async(dataset.dataset_slug)
