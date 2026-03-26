"""
Watcher configuration preview utilities.

Provides read-only testing of WatcherConfig without database side effects.
This module allows users to validate their watcher configuration by:
- Fetching the latest date from the configured API
- Calculating what dates would be backfilled
- Displaying formatted sample dates

No database writes occur during preview operations.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

import requests

from geomanager.models import Dataset
from geomanager.utils.date_utils import ensure_timezone_aware, PeriodUtilFactory
from geomanager.utils.parser_utils import UniversalDateParser
from geomanager.tasks.watchers import format_date_for_summary

logger = logging.getLogger("geomanager.watcher_preview")


@dataclass
class WatcherPreviewResult:
    """Container for preview test results"""

    success: bool
    latest_date: Optional[datetime] = None
    latest_date_formatted: Optional[str] = None
    first_dates: Optional[list[str]] = None
    last_dates: Optional[list[str]] = None
    total_count: int = 0
    period_type: Optional[str] = None
    has_start_year: bool = False
    dataset_context: Optional[list] = None
    existing_first_dates: Optional[list[str]] = None
    existing_last_dates: Optional[list[str]] = None
    existing_count: int = 0
    date_already_applied: Optional[bool] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None


def preview_watcher_config(config_dict: dict) -> WatcherPreviewResult:
    """
    Test watcher configuration without database writes.

    Args:
        config_dict: Dictionary containing watcher config fields
            - id: UUID or None (for unsaved configs)
            - api_url: URL to fetch from
            - parser_type: "direct_date_field" or "multi_field_constructor"
            - json_path: Path to date field (for direct parser)
            - date_format: Expected date format
            - year_field, month_field, day_field: Field names (for multi parser)
            - period_type: "dekadal" or "pentadal"
            - dataset_start_year: Starting year for backfill

    Returns:
        WatcherPreviewResult with success status and data or error info
    """

    # Step 1: Validate required fields
    validation_error = validate_config_fields(config_dict)
    if validation_error:
        return WatcherPreviewResult(success=False, error_message=validation_error, error_type="validation_error")

    # Step 2: Get dataset context if config has ID
    dataset_context = None
    existing_latest_date = None
    existing_first_dates = None
    existing_last_dates = None
    existing_count = 0
    primary_dataset = None  # First linked dataset — used for WmsDatasetIndex queries
    config_id = config_dict.get("id")

    if config_id:
        try:
            datasets = get_datasets_for_config(uuid.UUID(config_id))
            if datasets:
                primary_dataset = datasets[0]
                dataset_context = [{"id": str(ds.id), "title": ds.title, "slug": ds.dataset_slug} for ds in datasets]

                # Use the actual latest stored date from WmsDatasetIndex — the same
                # source fill_missing_dates uses — rather than dataset.latest_date,
                # which can be None or stale if data was ingested outside the watcher.
                from geomanager.models import WmsDatasetIndex

                latest_index = WmsDatasetIndex.objects.filter(dataset=primary_dataset).order_by("-datetime").first()
                existing_latest_date = latest_index.datetime if latest_index else None
        except (ValueError, Exception) as e:
            logger.warning(f"Could not get dataset context: {e}")

    # Step 3: Build parser config
    try:
        parser_config = build_parser_config_from_dict(config_dict)
    except Exception as e:
        return WatcherPreviewResult(
            success=False, error_message=f"Invalid parser configuration: {str(e)}", error_type="config_error"
        )

    # Step 4: Fetch latest date from API
    try:
        api_url = config_dict["api_url"]
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return WatcherPreviewResult(
            success=False,
            error_message="API request timed out after 30 seconds. The external API may be slow or unavailable.",
            error_type="timeout",
        )
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else "unknown"
        return WatcherPreviewResult(
            success=False,
            error_message=f"API returned HTTP {status_code}: {e.response.reason if e.response else 'Error'}. Please verify the API URL.",
            error_type="http_error",
        )
    except requests.RequestException as e:
        return WatcherPreviewResult(
            success=False, error_message=f"Failed to connect to API: {str(e)}", error_type="http_error"
        )
    except ValueError:
        return WatcherPreviewResult(
            success=False,
            error_message="API did not return valid JSON. Please check the API URL.",
            error_type="parse_error",
        )

    # Step 5: Parse the date
    try:
        latest_date = UniversalDateParser.parse(data, parser_config)
        latest_date_aware = ensure_timezone_aware(latest_date)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "no value" in error_msg.lower():
            json_path = config_dict.get("json_path", "configured path")
            return WatcherPreviewResult(
                success=False,
                error_message=f"Failed to parse date from API response. No value found at path '{json_path}'. Please check the Date Field Path configuration.",
                error_type="parse_error",
            )
        return WatcherPreviewResult(
            success=False, error_message=f"Date parsing error: {error_msg}", error_type="parse_error"
        )
    except Exception as e:
        return WatcherPreviewResult(
            success=False, error_message=f"Unexpected error parsing date: {str(e)}", error_type="parse_error"
        )

    # Step 6: Calculate backfill dates
    period_type = config_dict["period_type"]
    dataset_start_year = config_dict.get("dataset_start_year") or None

    try:
        backfill_dates = calculate_preview_dates(
            latest_date_aware, period_type, dataset_start_year, existing_latest_date
        )
    except ValueError as e:
        return WatcherPreviewResult(
            success=False,
            error_message=f"Invalid period type or date calculation error: {str(e)}",
            error_type="config_error",
        )
    except Exception as e:
        return WatcherPreviewResult(
            success=False, error_message=f"Error calculating dates: {str(e)}", error_type="config_error"
        )

    # Step 7: Get existing stored dates if dataset exists
    if primary_dataset:
        try:
            from geomanager.models import WmsDatasetIndex

            # Query existing dates
            existing_indices = (
                WmsDatasetIndex.objects.filter(dataset=primary_dataset)
                .order_by("datetime")
                .values_list("datetime", flat=True)
            )

            existing_count = existing_indices.count()
            logger.info(f"Found {existing_count} existing dates for dataset {primary_dataset.title}")

            if existing_count > 0:
                # Get first 5 and last 5
                if existing_count <= 10:
                    first_existing = list(existing_indices)
                    last_existing = []
                else:
                    first_existing = list(existing_indices[:5])
                    last_existing = list(existing_indices[existing_count - 5 : existing_count])

                logger.info(f"First existing dates: {first_existing[:3] if first_existing else 'none'}")

                # Format the dates - these are already datetime objects
                existing_first_dates = [format_date_for_summary(dt, period_type) for dt in first_existing]

                existing_last_dates = (
                    [format_date_for_summary(dt, period_type) for dt in last_existing] if last_existing else []
                )

                logger.info(f"Formatted first dates: {existing_first_dates}")
        except Exception as e:
            logger.error(f"Error fetching existing dates: {e}", exc_info=True)

    # Step 8: Format backfill dates for display
    total_count = len(backfill_dates)

    # Whether the latest API date is already fully reflected in the database.
    # True when there are no new dates to add AND the stored latest date covers
    # the API date — works for both start-year (backfill complete) and no-start-year
    # (append-only) configs.
    date_already_applied = None
    if existing_latest_date is not None:
        date_already_applied = total_count == 0 and existing_latest_date.date() >= latest_date_aware.date()

    # Get first 5 and last 5 dates to backfill
    if total_count <= 10:
        first_dates = backfill_dates
        last_dates = []
    else:
        first_dates = backfill_dates[:5]
        last_dates = backfill_dates[-5:]

    # Format dates using the summary formatter
    first_dates_formatted = [format_date_for_summary(datetime.combine(d, time.min), period_type) for d in first_dates]

    last_dates_formatted = (
        [format_date_for_summary(datetime.combine(d, time.min), period_type) for d in last_dates] if last_dates else []
    )

    # Format the latest date
    latest_date_formatted = format_date_for_summary(latest_date_aware, period_type)

    return WatcherPreviewResult(
        success=True,
        latest_date=latest_date_aware,
        latest_date_formatted=latest_date_formatted,
        first_dates=first_dates_formatted,
        last_dates=last_dates_formatted,
        total_count=total_count,
        period_type=period_type,
        has_start_year=bool(dataset_start_year),
        dataset_context=dataset_context,
        existing_first_dates=existing_first_dates,
        existing_last_dates=existing_last_dates,
        existing_count=existing_count,
        date_already_applied=date_already_applied,
    )


def validate_config_fields(config_dict: dict) -> Optional[str]:
    """
    Validate required configuration fields.

    Returns:
        Error message string if validation fails, None if valid
    """
    # Required for all configs
    if not config_dict.get("api_url"):
        return "API URL is required"

    parser_type = config_dict.get("parser_type")
    if not parser_type:
        return "Parser Type is required"

    if not config_dict.get("period_type"):
        return "Period Type is required"

    # dataset_start_year is optional — when absent, only the latest date is added (no backfill)

    # Parser-specific validation
    if parser_type == "direct_date_field":
        if not config_dict.get("json_path"):
            return "Date Field Path is required for direct_date_field parser"
    elif parser_type == "multi_field_constructor":
        if not config_dict.get("year_field"):
            return "Year Field is required for multi_field_constructor parser"
        if not config_dict.get("month_field"):
            return "Month Field is required for multi_field_constructor parser"
        if not config_dict.get("day_field"):
            return "Day Field is required for multi_field_constructor parser"

    return None


def get_datasets_for_config(config_id: uuid.UUID) -> list:
    """
    Find all datasets using this watcher config.

    Returns:
        List of Dataset instances (empty if none found)
    """
    try:
        return list(
            Dataset.objects.filter(watcher_config_id=config_id)
            .filter(dataset_slug__isnull=False)
            .exclude(dataset_slug="")
            .order_by("title")
        )
    except Exception as e:
        logger.warning(f"Error querying datasets for config {config_id}: {e}")
        return []


def build_parser_config_from_dict(config_dict: dict) -> dict:
    """
    Convert form data dict to parser config format.
    Mirrors WatcherConfig.get_parser_config() logic.

    Args:
        config_dict: Dictionary containing parser configuration fields

    Returns:
        Parser config dictionary suitable for UniversalDateParser
    """
    parser_type = config_dict.get("parser_type")

    if parser_type == "direct_date_field":
        config = {"json_path": config_dict.get("json_path", "")}
        if config_dict.get("date_format"):
            config["date_format"] = config_dict["date_format"]
        return config

    elif parser_type == "multi_field_constructor":
        return {
            "template": "{year}-{month:02d}-{day}",
            "field_mappings": {
                "year": config_dict.get("year_field", "end_year"),
                "month": config_dict.get("month_field", "end_month"),
                "day": config_dict.get("day_field", "end_dekad"),
            },
        }

    return {}


def calculate_preview_dates(
    latest_date: datetime,
    period_type: str,
    dataset_start_year: Optional[int],
    existing_latest_date: Optional[datetime] = None,
) -> list:
    """
    Calculate backfill dates without database access.
    Mirrors fill_missing_dates() logic but returns list instead of creating records.

    Args:
        latest_date: Latest date from API
        period_type: One of "dekadal", "pentadal", "weekly", "monthly"
        dataset_start_year: Starting year for backfill, or None to skip backfilling
        existing_latest_date: Latest existing date from WmsDatasetIndex (if any)

    Returns:
        List of date objects that would be backfilled (empty when dataset_start_year is None)
    """
    # No start year means no backfill — only the latest date will be added via create_date_index
    if not dataset_start_year:
        return []

    # Get period utility
    try:
        period_util = PeriodUtilFactory.get_util(period_type)
    except ValueError as e:
        raise ValueError(f"Invalid period type '{period_type}': {e}")

    # Determine start date for backfill
    if existing_latest_date:
        existing_date = existing_latest_date.date()
        if existing_date >= latest_date.date():
            # No backfill needed
            return []
        next_start_date = period_util.calculate_next_period_date(existing_date)
    else:
        # No existing data, start from dataset_start_year
        next_start_date = datetime(dataset_start_year, 1, 1).date()

    if next_start_date > latest_date.date():
        # Start date is after latest date, no backfill needed
        return []

    # Mirror fill_missing_dates exactly: use generate_from_anchor for period types
    # that need an exact start anchor (e.g. weekly), so the preview shows the same
    # dates the watcher would actually create.
    if hasattr(period_util, "generate_from_anchor"):
        dates_to_create = period_util.generate_from_anchor(next_start_date, latest_date.date())
    else:
        dates_to_create = period_util.generate_dates(
            next_start_date.year, latest_date.year, latest_date.month, latest_date.day
        )
        dates_to_create = [d for d in dates_to_create if next_start_date <= d <= latest_date.date()]

    return dates_to_create
