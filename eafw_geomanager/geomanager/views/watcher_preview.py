"""
Preview and trigger endpoints for WatcherConfig testing and manual updates.

Provides AJAX endpoints that allow users to:
- Test their watcher configuration before saving (preview)
- Manually trigger an immediate update for all datasets using a config (trigger)
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from wagtail.admin.auth import user_passes_test, user_has_any_page_permission

from geomanager.utils.watcher_preview import preview_watcher_config

logger = logging.getLogger("geomanager.watcher_preview")


@require_http_methods(["POST"])
@user_passes_test(user_has_any_page_permission)
def preview_watcher_config_view(request):
    """
    AJAX endpoint for testing WatcherConfig without saving.

    Method: POST
    Content-Type: application/json

    Request Body:
        {
            "id": "uuid-or-null",           // Config ID (null for unsaved)
            "api_url": "https://...",        // Required
            "parser_type": "direct_date_field",  // Required
            "json_path": "data.date",        // For direct_date_field
            "date_format": "yyyy-MM-dd",     // For direct_date_field
            "year_field": "end_year",        // For multi_field_constructor
            "month_field": "end_month",      // For multi_field_constructor
            "day_field": "end_dekad",        // For multi_field_constructor
            "period_type": "dekadal",        // Required
            "dataset_start_year": 2000       // Required
        }

    Success Response (200):
        {
            "success": true,
            "latest_date": "2025-11-21T00:00:00Z",
            "latest_date_formatted": "3rd Dekad of November 2025",
            "first_dates": [
                "1st Dekad of January 2000",
                "2nd Dekad of January 2000",
                ...
            ],
            "last_dates": [
                "1st Dekad of November 2025",
                "2nd Dekad of November 2025",
                ...
            ],
            "total_count": 310,
            "period_type": "dekadal",
            "dataset_context": {
                "id": "uuid",
                "title": "CDI Dataset",
                "slug": "cdi"
            }
        }

    Error Response (200 or 400):
        {
            "success": false,
            "error": "User-friendly error message",
            "error_type": "timeout" | "http_error" | "parse_error" | "validation_error" | "config_error"
        }
    """
    try:
        # Parse JSON body
        try:
            config_dict = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON in request body", "error_type": "validation_error"},
                status=400,
            )

        # Log the preview request
        logger.info(f"Preview request from user {request.user.username} for config ID: {config_dict.get('id', 'new')}")

        # Call preview utility
        result = preview_watcher_config(config_dict)

        # Return error response if preview failed
        if not result.success:
            logger.warning(f"Preview failed: {result.error_type} - {result.error_message}")
            return JsonResponse({"success": False, "error": result.error_message, "error_type": result.error_type})

        # Build success response
        response_data = {
            "success": True,
            "latest_date": result.latest_date.isoformat() if result.latest_date else None,
            "latest_date_formatted": result.latest_date_formatted,
            "first_dates": result.first_dates,
            "last_dates": result.last_dates,
            "total_count": result.total_count,
            "period_type": result.period_type,
            "has_start_year": result.has_start_year,
            "dataset_context": result.dataset_context,
            "existing_first_dates": result.existing_first_dates,
            "existing_last_dates": result.existing_last_dates,
            "existing_count": result.existing_count,
            "date_already_applied": result.date_already_applied,
        }

        logger.info(f"Preview successful: {result.total_count} dates calculated")
        return JsonResponse(response_data)

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in preview endpoint: {str(e)}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": "An unexpected error occurred. Please try again or contact support.",
                "error_type": "unknown_error",
            },
            status=500,
        )


@require_http_methods(["POST"])
@user_passes_test(user_has_any_page_permission)
def trigger_watcher_update_view(request):
    """
    Trigger an immediate watcher update for all datasets linked to a WatcherConfig.

    Runs synchronously so the caller gets per-dataset success/failure feedback.
    Configs with dataset_start_year will backfill missing dates; configs without
    will only add/update the date if the API returns something newer than stored.

    Method: POST
    Content-Type: application/json

    Request Body:
        {"config_id": "<uuid>"}

    Success Response:
        {
            "success": true,
            "updated": 2,
            "failed": 0,
            "datasets": [
                {"slug": "...", "title": "...", "success": true},
                ...
            ]
        }
    """
    try:
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON in request body", "error_type": "validation_error"},
                status=400,
            )

        config_id = body.get("config_id")
        if not config_id:
            return JsonResponse(
                {"success": False, "error": "config_id is required", "error_type": "validation_error"},
                status=400,
            )

        from geomanager.models import WatcherConfig

        try:
            config = WatcherConfig.objects.get(id=config_id)
        except (WatcherConfig.DoesNotExist, Exception):
            return JsonResponse(
                {"success": False, "error": "Watcher configuration not found", "error_type": "not_found"},
                status=404,
            )

        datasets = list(
            config.datasets.filter(dataset_slug__isnull=False).exclude(dataset_slug="").only("dataset_slug", "title")
        )

        if not datasets:
            return JsonResponse(
                {
                    "success": False,
                    "error": "No datasets are linked to this configuration yet",
                    "error_type": "no_datasets",
                }
            )

        from geomanager.tasks.watchers import update_dataset_date

        results = []
        success_count = 0
        failed_count = 0

        for dataset in datasets:
            ok = update_dataset_date(dataset.dataset_slug, triggered_by="cms")
            results.append({"slug": dataset.dataset_slug, "title": dataset.title, "success": ok})
            if ok:
                success_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Manual trigger by {request.user.username} for config '{config.title}': "
            f"{success_count} updated, {failed_count} failed"
        )

        return JsonResponse({"success": True, "updated": success_count, "failed": failed_count, "datasets": results})

    except Exception as e:
        logger.error(f"Unexpected error in trigger endpoint: {str(e)}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "An unexpected error occurred.", "error_type": "unknown_error"},
            status=500,
        )
