"""Orchestrate CAP alert draft creation from FloodWatch data sources."""

from datetime import timedelta
from django.utils import timezone

from .gatherer import get_assessment_for_cap, get_forecast_alerts_for_cap
from .mapper import get_cap_fields
from .area_builder import build_cap_areas_for_country


def create_cap_draft_from_assessment(assessment_id, expires_hours=48):
    """
    Create a draft CAP alert from a published expert assessment.

    Returns a CapAlertPage (draft, unpublished) or raises ValueError.
    """
    assessment = get_assessment_for_cap(assessment_id)
    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found or not published")

    cap_fields = get_cap_fields(assessment.risk_level)
    areas = build_cap_areas_for_country(assessment.country_code, assessment.country_name)

    now = timezone.now()
    onset = assessment.valid_from or assessment.assessment_date
    expires = assessment.valid_to or (now + timedelta(hours=expires_hours))

    description = assessment.assessment_comment
    if assessment.affected_areas:
        description += f"\n\nAffected areas: {assessment.affected_areas}"

    instruction = assessment.recommendations or (
        "Monitor water levels and follow local authority guidance."
    )

    alert_data = {
        "sender": "info@icpac.net",
        "sent": now.isoformat(),
        "status": "Draft",
        "msgType": "Alert",
        "scope": "Public",
        "info": [{
            "language": "en",
            "category": "Met",
            "event": "Flood",
            "responseType": ["Monitor"],
            "urgency": cap_fields["urgency"],
            "severity": cap_fields["severity"],
            "certainty": cap_fields["certainty"],
            "effective": now.isoformat(),
            "onset": onset.isoformat() if hasattr(onset, 'isoformat') else str(onset),
            "expires": expires.isoformat() if hasattr(expires, 'isoformat') else str(expires),
            "senderName": "ICPAC",
            "headline": f"Flood {assessment.risk_level.title()} - {assessment.country_name}",
            "description": description.strip(),
            "instruction": instruction.strip(),
            "area": areas,
        }],
    }

    from capcomposer.cap.utils import create_draft_alert_from_alert_data
    cap_page = create_draft_alert_from_alert_data(alert_data, update_event_list=True)
    if not cap_page:
        raise ValueError("Failed to create CAP draft — CapAlertListPage may not exist")
    return cap_page


def create_cap_draft_from_forecast(country_code=None, expires_hours=48):
    """
    Create CAP alert drafts from live multimodal forecast data.

    Queries the current forecast, groups by country, and creates a CAP draft
    for each country with at least one point at warning level or above.

    Args:
        country_code: Optional ISO-2 code to limit to one country.
        expires_hours: Hours until the alert expires.

    Returns:
        list of dicts with {country, risk_level, cap_page_id, edit_url}
    """
    alerts = get_forecast_alerts_for_cap(country_code=country_code, min_level="warning")
    if not alerts:
        return []

    now = timezone.now()
    results = []

    for alert in alerts:
        cap_fields = get_cap_fields(alert.risk_level)
        areas = build_cap_areas_for_country(alert.country_code_iso3, alert.country_name)

        # Build human-readable description from forecast data
        parts = [
            f"Flood forecast for {alert.country_name} based on multimodal "
            f"hydrological model ensemble (data date: {alert.data_date}, "
            f"forecast date: {alert.forecast_date}).",
            "",
            f"Monitoring points summary ({alert.total_points} total):",
        ]
        if alert.emergency_count:
            parts.append(f"  - Emergency (>= 750 m³/s): {alert.emergency_count} points")
        if alert.alarm_count:
            parts.append(f"  - Alarm (>= 500 m³/s): {alert.alarm_count} points")
        if alert.warning_count:
            parts.append(f"  - Warning (>= 300 m³/s): {alert.warning_count} points")
        parts.append(f"  - Normal: {alert.normal_count} points")
        parts.append(f"\nMaximum forecast discharge: {alert.max_daily_avg:.0f} m³/s")

        description = "\n".join(parts)

        instruction = (
            "Monitor water levels at local river gauges. "
            "Follow evacuation guidance from local authorities. "
            "Avoid crossing flooded rivers and waterways."
        )

        onset = alert.forecast_date
        expires = now + timedelta(hours=expires_hours)

        alert_data = {
            "sender": "info@icpac.net",
            "sent": now.isoformat(),
            "status": "Draft",
            "msgType": "Alert",
            "scope": "Public",
            "info": [{
                "language": "en",
                "category": "Met",
                "event": "Flood",
                "responseType": ["Monitor", "Prepare"],
                "urgency": cap_fields["urgency"],
                "severity": cap_fields["severity"],
                "certainty": cap_fields["certainty"],
                "effective": now.isoformat(),
                "onset": onset.isoformat() if hasattr(onset, 'isoformat') else str(onset),
                "expires": expires.isoformat() if hasattr(expires, 'isoformat') else str(expires),
                "senderName": "ICPAC",
                "headline": (
                    f"Flood {alert.risk_level.title()} - {alert.country_name} "
                    f"({alert.emergency_count + alert.alarm_count + alert.warning_count} "
                    f"alert points)"
                ),
                "description": description,
                "instruction": instruction,
                "area": areas,
            }],
        }

        try:
            from capcomposer.cap.utils import create_draft_alert_from_alert_data
            cap_page = create_draft_alert_from_alert_data(alert_data, update_event_list=True)
            if cap_page:
                results.append({
                    "country": alert.country_name,
                    "country_code": alert.country_code,
                    "risk_level": alert.risk_level,
                    "emergency_count": alert.emergency_count,
                    "alarm_count": alert.alarm_count,
                    "warning_count": alert.warning_count,
                    "cap_alert_id": cap_page.pk,
                    "edit_url": f"/admin/pages/{cap_page.pk}/edit/",
                })
        except Exception as e:
            results.append({
                "country": alert.country_name,
                "country_code": alert.country_code,
                "risk_level": alert.risk_level,
                "error": str(e),
            })

    return results
