"""
Dataset watcher system for monitoring and updating geospatial datasets from external APIs.

This module handles:
- Fetching latest dates from configured APIs
- Backfilling missing historical dates
- Updating dataset indices
- Batch processing of multiple datasets
"""

import calendar
import logging
import requests
from datetime import datetime, time, timedelta
from geomanager.models import Dataset, WmsDatasetIndex
from geomanager.utils.date_utils import ensure_timezone_aware, PeriodUtilFactory
from geomanager.utils.parser_utils import UniversalDateParser

logger = logging.getLogger("geomanager.watchers")


def fill_missing_dates(dataset, latest_date):
    if not dataset.dataset_slug:
        logger.warning(f"Dataset '{dataset.title}' has no slug")
        return 0

    # Determine period type from watcher configuration
    if not dataset.watcher_config:
        logger.warning(f"Dataset '{dataset.dataset_slug}' has no watcher_config")
        return 0

    # Skip backfilling entirely when no start year is configured.
    # create_date_index (called after this function) still adds the latest date.
    if not dataset.watcher_config.dataset_start_year:
        return 0

    period_type = dataset.watcher_config.period_type
    try:
        period_util = PeriodUtilFactory.get_util(period_type)
    except ValueError as e:
        logger.error(f"Invalid period type for dataset '{dataset.dataset_slug}': {e}")
        return 0

    # Get the latest existing date
    latest_existing = dataset.wms_datasets.order_by("-datetime").first()

    if latest_existing:
        latest_existing_date = latest_existing.datetime.date()
        if latest_existing_date >= latest_date.date():
            return 0
        next_start_date = period_util.calculate_next_period_date(latest_existing_date)
    else:
        next_start_date = datetime(dataset.watcher_config.dataset_start_year, 1, 1).date()

    if next_start_date > latest_date.date():
        return 0

    # For period types that need an exact anchor (e.g. weekly), use generate_from_anchor
    # so the 7-day cadence aligns to the dataset's own day-of-week rather than Jan 1.
    if hasattr(period_util, "generate_from_anchor"):
        dates_to_create = period_util.generate_from_anchor(next_start_date, latest_date.date())
    else:
        dates_to_create = period_util.generate_dates(
            next_start_date.year, latest_date.year, latest_date.month, latest_date.day
        )
        dates_to_create = [d for d in dates_to_create if next_start_date <= d <= latest_date.date()]

    if not dates_to_create:
        return 0

    # Batch check existing dates to avoid N+1 queries
    existing_dates = set(
        dataset.wms_datasets.filter(datetime__date__in=dates_to_create).values_list("datetime__date", flat=True)
    )

    # Bulk create missing date entries
    new_entries = [
        WmsDatasetIndex(datetime=ensure_timezone_aware(datetime.combine(d, time.min)), dataset=dataset)
        for d in dates_to_create
        if d not in existing_dates
    ]

    if new_entries:
        WmsDatasetIndex.objects.bulk_create(new_entries, ignore_conflicts=True)
        logger.info(
            f"Backfilled {len(new_entries)} dates for '{dataset.dataset_slug}' "
            f"({dates_to_create[0]} to {dates_to_create[-1]})"
        )

    return len(new_entries)


def should_update_dataset_cms(dataset):
    """Check if a dataset can be updated (for CMS-triggered updates)."""
    if not dataset.dataset_slug:
        return False, "No dataset_slug configured"

    if not dataset.watcher_config:
        return False, "No watcher configuration attached"

    if not dataset.watcher_config.api_url:
        return False, "No API URL configured in watcher_config"

    return True, "Ready for CMS-triggered update"


def should_update_dataset_periodic(dataset):
    """Check if a dataset should be updated (for periodic/scheduled updates)."""
    if not dataset.dataset_slug:
        return False, "No dataset_slug configured"

    if not dataset.watcher_config:
        return False, "No watcher configuration attached"

    if not dataset.watcher_config.auto_update_frequency:
        return False, "Auto-update disabled (no frequency set)"

    if not dataset.watcher_config.api_url:
        return False, "No API URL configured in watcher_config"

    return True, "Ready for periodic update"


def fetch_latest_date_from_api(dataset):
    """Fetch and parse the latest date from dataset's API."""
    if not dataset.watcher_config:
        raise ValueError(f"Dataset '{dataset.dataset_slug}' has no watcher_config")

    resp = requests.get(dataset.watcher_config.api_url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Parse date using universal parser
    parser_config = dataset.get_parser_config()
    latest_date = UniversalDateParser.parse(data, parser_config)
    latest_date_aware = ensure_timezone_aware(latest_date)

    return latest_date_aware


def update_dataset_latest_date(dataset, new_date):
    """Update dataset's latest_date field and summary if the new date is newer.

    Uses QuerySet.update() instead of instance.save() to avoid firing post_save
    signals and triggering an infinite cascade.
    """
    date_changed = not dataset.latest_date or dataset.latest_date < new_date

    if dataset.watcher_config:
        period_type = dataset.watcher_config.period_type
        formatted_date = format_date_for_summary(new_date, period_type)
        new_summary = f"Latest: {formatted_date}"

        if date_changed or dataset.summary != new_summary:
            Dataset.objects.filter(pk=dataset.pk).update(
                latest_date=new_date,
                summary=new_summary,
            )
            return True
    elif date_changed:
        Dataset.objects.filter(pk=dataset.pk).update(latest_date=new_date)
        return True

    return False


def format_date_for_summary(date, period_type):
    """Format date in human-readable format based on period type."""
    month_name = date.strftime("%B")
    year = date.year
    day = date.day

    if period_type == "dekadal":
        if day <= 10:
            dekad = "1st"
        elif day <= 20:
            dekad = "2nd"
        else:
            dekad = "3rd"
        return f"{dekad} Dekad of {month_name} {year}"

    elif period_type == "pentadal":
        pentad_num = ((day - 1) // 5) + 1
        return f"{get_ordinal(pentad_num)} Pentad of {month_name} {year}"

    elif period_type == "weekly":
        end_date = date + timedelta(days=7)
        return f"{date.strftime('%d %b %Y')} To {end_date.strftime('%d %b %Y')}"

    elif period_type == "monthly":
        next_month = date.month % 12 + 1
        next_month_name = calendar.month_name[next_month]
        init_month = date.strftime("%b")
        return f"{next_month_name} (Initialized {init_month}-{year})"

    else:
        return f"{month_name} {year}"


def get_ordinal(n):
    """Convert number to ordinal (1 -> 1st, 2 -> 2nd, etc.)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def create_date_index(dataset, datetime_aware):
    """Create a new date index entry for the dataset if it doesn't exist.

    Uses get_or_create to be safe under concurrent threads/processes — if two
    workers race here, one gets the created object and the other gets the
    existing one; neither raises an IntegrityError.
    """
    _, created = WmsDatasetIndex.objects.get_or_create(
        datetime=datetime_aware,
        dataset=dataset,
    )
    return created


def update_dataset_date(dataset_slug, triggered_by="periodic"):
    """
    Update a single dataset with the latest date from its configured API.

    Returns True on success, False on failure. Uses QuerySet.update() for all
    timestamp writes to avoid firing post_save signals.
    """
    from django.utils import timezone

    dataset = Dataset.objects.select_related("watcher_config").filter(dataset_slug=dataset_slug).first()
    if not dataset:
        logger.warning(f"Dataset '{dataset_slug}' not found in database")
        return False

    if triggered_by == "cms":
        should_update, reason = should_update_dataset_cms(dataset)
    else:
        should_update, reason = should_update_dataset_periodic(dataset)

    if not should_update:
        return False

    try:
        latest_date_aware = fetch_latest_date_from_api(dataset)

        fill_missing_dates(dataset, latest_date_aware)

        update_dataset_latest_date(dataset, latest_date_aware)

        # create_date_index is only needed for irregular datasets (no dataset_start_year)
        # where fill_missing_dates is a no-op. For regular datasets (dekadal, monthly,
        # pentadal etc.) fill_missing_dates normalises dates to midnight of the period
        # start day — calling create_date_index with the raw API datetime (e.g. 09:00)
        # would add a second entry for the same period alongside the midnight one.
        if not dataset.watcher_config.dataset_start_year:
            create_date_index(dataset, latest_date_aware)

        # Use QuerySet.update() — bypasses post_save signal, prevents cascade
        Dataset.objects.filter(pk=dataset.pk).update(last_watcher_update=timezone.now())

        logger.info(f"Updated '{dataset_slug}' (triggered by: {triggered_by})")
        return True

    except requests.RequestException as e:
        logger.error(f"HTTP error updating '{dataset_slug}': {str(e)}")
    except ValueError as e:
        logger.error(f"Date parsing error for '{dataset_slug}': {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error updating '{dataset_slug}': {str(e)}", exc_info=True)

    return False


def get_datasets_for_update():
    """Query all datasets configured for auto-update."""
    return (
        Dataset.objects.select_related("watcher_config")
        .filter(watcher_config__isnull=False, watcher_config__auto_update_frequency__isnull=False)
        .exclude(watcher_config__api_url="")
        .exclude(watcher_config__api_url__isnull=True)
    )


def update_all_datasets():
    """Update all configured datasets that have auto-update enabled."""
    active_datasets = list(get_datasets_for_update())

    if not active_datasets:
        logger.warning("No datasets configured for auto-update")
        return

    logger.info(f"Batch updating {len(active_datasets)} dataset(s)")

    success_count = 0
    error_count = 0

    for dataset in active_datasets:
        if not dataset.dataset_slug:
            logger.warning(f"Dataset '{dataset.title}' has no dataset_slug")
            error_count += 1
            continue

        success = update_dataset_date(dataset.dataset_slug)
        if success:
            success_count += 1
        else:
            error_count += 1

    logger.info(f"Batch complete: {success_count} successful, {error_count} failed")
