"""
Periodic watcher scheduler using a singleton WatcherScheduler backed by a
bounded ThreadPoolExecutor.

Design principles:
- Single scheduler thread owns all scheduling decisions.
- A bounded ThreadPoolExecutor (not raw threads) executes updates.
- Per-process deduplication via a futures dict (no duplicate submissions within a process).
- Cross-process deduplication via the DB field last_watcher_update — a process
  that checks _get_due_datasets() after another process has already stamped the
  timestamp will see it as not due.
- Signal-triggered updates use triggered_by="cms" (no frequency check required).
- Periodic updates use triggered_by="periodic" (frequency check applies).
- No signals are fired from within the watcher because watchers.py uses
  QuerySet.update() for all timestamp writes.
"""

import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("geomanager.periodic")

CHECK_INTERVAL = getattr(settings, "WATCHER_CHECK_INTERVAL", 300)  # seconds
MAX_WORKERS = getattr(settings, "WATCHER_MAX_WORKERS", 4)


class WatcherScheduler:
    """
    Singleton scheduler that manages periodic dataset updates.

    A single daemon thread runs the scheduling loop. Actual updates are
    submitted to a bounded ThreadPoolExecutor so the number of concurrent
    update threads is always capped at MAX_WORKERS.

    Multi-process note: each gunicorn/daphne worker has its own instance and
    its own futures dict. Cross-process deduplication is provided by the
    last_watcher_update DB timestamp checked in _get_due_datasets().
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix="watcher-worker",
        )
        self._futures: dict[str, Future] = {}
        self._futures_lock = threading.Lock()
        self._started = False

    @classmethod
    def get_instance(cls) -> "WatcherScheduler":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def start(self):
        """Start the periodic scheduler thread. Idempotent — safe to call multiple times."""
        with self._instance_lock:
            if self._started:
                return
            self._started = True

        thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="watcher-scheduler",
        )
        thread.start()
        logger.info(f"WatcherScheduler started (interval={CHECK_INTERVAL}s, max_workers={MAX_WORKERS})")

    def submit(self, dataset_slug: str, triggered_by: str = "cms") -> bool:
        """
        Submit a dataset for update if not already running in this process.

        Args:
            dataset_slug: The dataset to update.
            triggered_by: "cms" (signal/manual, skips frequency check) or
                          "periodic" (scheduler, requires auto_update_frequency).

        Returns True if submitted, False if already running.
        """
        with self._futures_lock:
            existing = self._futures.get(dataset_slug)
            if existing and not existing.done():
                logger.debug(f"'{dataset_slug}' already running, skipping")
                return False

            future = self._executor.submit(self._run_update, dataset_slug, triggered_by)
            self._futures[dataset_slug] = future
            return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_update(self, dataset_slug: str, triggered_by: str):
        """Worker function — runs inside the thread pool."""
        from geomanager.tasks.watchers import update_dataset_date

        try:
            update_dataset_date(dataset_slug, triggered_by=triggered_by)
        except Exception as e:
            logger.error(f"Unhandled error updating '{dataset_slug}': {e}", exc_info=True)

    def _get_due_datasets(self):
        """
        Return datasets that are due for a periodic update.

        Frequency varies per dataset so the due check is done in Python after
        a single DB query with select_related (no N+1).
        """
        from geomanager.models import Dataset

        candidates = (
            Dataset.objects.select_related("watcher_config")
            .filter(
                dataset_slug__isnull=False,
                watcher_config__isnull=False,
                watcher_config__auto_update_frequency__isnull=False,
            )
            .exclude(dataset_slug="")
            .exclude(watcher_config__api_url="")
            .exclude(watcher_config__api_url__isnull=True)
        )

        now = timezone.now()
        due = []

        for dataset in candidates:
            # Never been updated — due immediately
            if not dataset.last_watcher_update:
                due.append(dataset)
                continue

            interval = timedelta(minutes=dataset.watcher_config.auto_update_frequency)
            if (now - dataset.last_watcher_update) >= interval:
                due.append(dataset)

        return due

    def _scheduler_loop(self):
        """
        Main scheduling loop. Runs in a single daemon thread.
        Checks every CHECK_INTERVAL seconds which datasets are due and submits them.
        """
        logger.info("Scheduler loop running")

        while True:
            try:
                due = self._get_due_datasets()
                for dataset in due:
                    self.submit(dataset.dataset_slug, triggered_by="periodic")

                if due:
                    logger.debug(f"Submitted {len(due)} dataset(s) for periodic update")

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)

            time.sleep(CHECK_INTERVAL)


def start_periodic_watchers():
    """Entry point called from apps.py."""
    WatcherScheduler.get_instance().start()
