"""
Dataset watcher system for monitoring and updating geospatial datasets from external APIs.

This module handles:
- Fetching latest dates from configured APIs
- Backfilling missing historical dates
- Updating dataset indices
- Batch processing of multiple datasets
"""

import logging
import requests
from datetime import datetime, time
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

    # Generate periodic dates in the range
    dates_to_create = period_util.generate_dates(
        next_start_date.year, latest_date.year, latest_date.month, latest_date.day
    )

    # Filter to only include dates from next_start_date onwards
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
    """Update dataset's latest_date field and summary if the new date is newer."""
    date_changed = False

    if not dataset.latest_date or dataset.latest_date < new_date:
        dataset.latest_date = new_date
        date_changed = True

    # Always update summary to reflect current configuration
    if dataset.watcher_config:
        period_type = dataset.watcher_config.period_type
        formatted_date = format_date_for_summary(new_date, period_type)
        new_summary = f"Latest: {formatted_date}"

        # Update summary if it changed or date changed
        if dataset.summary != new_summary or date_changed:
            dataset.summary = new_summary
            dataset.save(update_fields=["latest_date", "summary"])
            return True
    elif date_changed:
        dataset.save(update_fields=["latest_date"])
        return True

    return False


def format_date_for_summary(date, period_type):
    """Format date in human-readable format like '1st Dekad of May 2025'."""
    month_name = date.strftime("%B")  # Full month name
    year = date.year
    day = date.day

    if period_type == "dekadal":
        # Determine which dekad (1-10 = 1st, 11-20 = 2nd, 21+ = 3rd)
        if day <= 10:
            dekad = "1st"
        elif day <= 20:
            dekad = "2nd"
        else:
            dekad = "3rd"
        return f"{dekad} Dekad of {month_name} {year}"

    elif period_type == "pentadal":
        # Determine which pentad (1-5 = 1st, 6-10 = 2nd, etc.)
        pentad_num = ((day - 1) // 5) + 1
        ordinal = get_ordinal(pentad_num)
        return f"{ordinal} Pentad of {month_name} {year}"

    else:
        # For monthly or other period types, just use month and year
        return f"{month_name} {year}"


def get_ordinal(n):
    """Convert number to ordinal (1 -> 1st, 2 -> 2nd, etc.)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def create_date_index(dataset, datetime_aware):
    """Create a new date index entry for the dataset if it doesn't exist."""
    if not dataset.wms_datasets.filter(datetime=datetime_aware).exists():
        WmsDatasetIndex.objects.create(datetime=datetime_aware, dataset=dataset)
        return True
    return False


def update_dataset_date(dataset_slug, triggered_by="periodic"):
    """
    Update a single dataset with the latest date from its configured API.
    """
    # Fetch dataset
    dataset = Dataset.objects.filter(dataset_slug=dataset_slug).first()
    if not dataset:
        logger.warning(f"Dataset '{dataset_slug}' not found in database")
        return

    # Use appropriate validation based on trigger source
    if triggered_by == "cms":
        should_update, reason = should_update_dataset_cms(dataset)
    else:
        should_update, reason = should_update_dataset_periodic(dataset)

    if not should_update:
        return

    try:
        # Fetch latest date from API
        latest_date_aware = fetch_latest_date_from_api(dataset)

        # Fill missing dates (for periodic datasets)
        fill_missing_dates(dataset, latest_date_aware)

        # Update dataset's latest_date field
        update_dataset_latest_date(dataset, latest_date_aware)

        # Create new date index
        create_date_index(dataset, latest_date_aware)

        # Update last_watcher_update timestamp
        from django.utils import timezone

        dataset.last_watcher_update = timezone.now()
        dataset.save(update_fields=["last_watcher_update"])

        logger.info(f"Updated '{dataset_slug}' (triggered by: {triggered_by})")

    except requests.RequestException as e:
        logger.error(f"HTTP error updating '{dataset_slug}': {str(e)}")
    except ValueError as e:
        logger.error(f"Date parsing error for '{dataset_slug}': {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error updating '{dataset_slug}': {str(e)}", exc_info=True)


def get_datasets_for_update():
    """Query all datasets configured for auto-update."""
    return (
        Dataset.objects.filter(watcher_config__isnull=False, watcher_config__auto_update_frequency__isnull=False)
        .exclude(watcher_config__api_url="")
        .exclude(watcher_config__api_url__isnull=True)
    )


def update_all_datasets():
    """Update all configured datasets that have auto-update enabled."""
    active_datasets = get_datasets_for_update()
    dataset_count = active_datasets.count()

    if dataset_count == 0:
        logger.warning("No datasets configured for auto-update")
        return

    logger.info(f"Batch updating {dataset_count} dataset(s)")

    success_count = 0
    error_count = 0

    for dataset in active_datasets:
        if dataset.dataset_slug:
            try:
                update_dataset_date(dataset.dataset_slug)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to update '{dataset.dataset_slug}': {str(e)}")
                error_count += 1
        else:
            logger.warning(f"Dataset '{dataset.title}' has no dataset_slug")
            error_count += 1

    logger.info(f"Batch complete: {success_count} successful, {error_count} failed")
