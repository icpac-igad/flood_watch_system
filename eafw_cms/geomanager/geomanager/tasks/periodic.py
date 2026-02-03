"""
Periodic watcher system for per-dataset update scheduling.

This module implements a polling loop that:
- Tracks each dataset's last update time via database field
- Checks every WATCHER_CHECK_INTERVAL(seconds) which datasets are due for update
- Updates only datasets where (now - last_watcher_update) >= auto_update_frequency
"""

import time
import threading
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("geomanager.periodic")

# Configuration defaults to 300 seconds (5 minutes)
CHECK_INTERVAL = getattr(settings, "WATCHER_CHECK_INTERVAL", 300)  # In seconds, default 5 minutes

# Track active update threads
active_updates = {}
active_updates_lock = threading.Lock()


def is_dataset_due_for_update(dataset):
    if not dataset.watcher_config:
        return False
    if not dataset.watcher_config.auto_update_frequency:
        return False
    if not dataset.dataset_slug or not dataset.watcher_config.api_url:
        return False

    # If never updated, it's due
    if not dataset.last_watcher_update:
        return True

    # Check if enough time has elapsed
    now = timezone.now()
    time_since_update = now - dataset.last_watcher_update
    update_interval = timedelta(minutes=dataset.watcher_config.auto_update_frequency)

    return time_since_update >= update_interval


def update_dataset_with_tracking(dataset_slug):
    """
    Update a dataset and track the update time.
    This runs in a background thread.
    """
    from geomanager.tasks.watchers import update_dataset_date

    try:
        update_dataset_date(dataset_slug, triggered_by="periodic")
    except Exception as e:
        logger.error(f"Error updating '{dataset_slug}': {str(e)}", exc_info=True)
    finally:
        # Remove from active updates
        with active_updates_lock:
            if dataset_slug in active_updates:
                del active_updates[dataset_slug]


def start_dataset_update_thread(dataset_slug):
    """
    Start a background thread to update a dataset.
    Prevents duplicate updates for the same dataset.
    """
    with active_updates_lock:
        # Don't start if already updating
        if dataset_slug in active_updates:
            return False

        # Start the update thread
        thread = threading.Thread(
            target=update_dataset_with_tracking, args=(dataset_slug,), daemon=True, name=f"watcher-{dataset_slug}"
        )
        active_updates[dataset_slug] = thread
        thread.start()
        logger.info(f"Started update thread for '{dataset_slug}'")
        return True


def watcher_loop():
    """
    Loop that checks datasets individually and updates based on their frequency independently.
    """
    from geomanager.models import Dataset

    initial_datasets = (
        Dataset.objects.filter(watcher_config__isnull=False, watcher_config__auto_update_frequency__isnull=False)
        .exclude(watcher_config__api_url="")
        .exclude(watcher_config__api_url__isnull=True)
    )

    initial_count = initial_datasets.count()
    logger.info(f"Periodic watcher started: {initial_count} dataset(s) configured")

    for dataset in initial_datasets:
        if dataset.dataset_slug:
            start_dataset_update_thread(dataset.dataset_slug)
            time.sleep(1)  # Stagger startup updates

    # Main loop
    while True:
        try:
            # Query all datasets with auto-update enabled
            datasets = (
                Dataset.objects.filter(
                    watcher_config__isnull=False, watcher_config__auto_update_frequency__isnull=False
                )
                .exclude(watcher_config__api_url="")
                .exclude(watcher_config__api_url__isnull=True)
            )

            for dataset in datasets:
                if not dataset.dataset_slug:
                    continue

                # Check if this dataset is due for update
                if is_dataset_due_for_update(dataset):
                    start_dataset_update_thread(dataset.dataset_slug)

            # Sleep for check interval
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            logger.error(f"Error in watcher loop: {str(e)}", exc_info=True)
            time.sleep(60)


def start_periodic_watchers():
    """
    Start the periodic watcher in a background thread.
    """
    thread = threading.Thread(target=watcher_loop, daemon=True, name="watcher-main")
    thread.start()
    logger.info("Periodic watcher thread started")
