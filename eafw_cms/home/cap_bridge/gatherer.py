"""Query forecast and expert assessment data from DB for CAP alert generation."""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, date

from django.db import connection

# Same thresholds as the API (multimodal.py)
WARNING_THRESHOLD = 300.0
ALARM_THRESHOLD = 500.0
EMERGENCY_THRESHOLD = 750.0

# ISO-3 to ISO-2 mapping (gha.admin0 uses ISO-3 in gid_0)
ISO3_TO_ISO2 = {
    "BDI": "BI", "DJI": "DJ", "ERI": "ER", "ETH": "ET",
    "KEN": "KE", "RWA": "RW", "SOM": "SO", "SSD": "SS",
    "SDN": "SD", "TZA": "TZ", "UGA": "UG",
}


@dataclass
class AssessmentForCAP:
    assessment_id: int
    expert_type: str
    assessment_date: date
    valid_from: Optional[date]
    valid_to: Optional[date]
    country_name: str
    country_code: str
    risk_level: str
    assessment_comment: str
    affected_areas: str
    recommendations: str


@dataclass
class ForecastAlertForCAP:
    """Alert data derived from multimodal forecast points for a country."""
    country_code: str       # ISO-2 (e.g. "KE")
    country_code_iso3: str  # ISO-3 (e.g. "KEN")
    country_name: str
    forecast_date: date
    data_date: date
    risk_level: str         # highest level: emergency > alarm > warning > normal
    total_points: int
    emergency_count: int
    alarm_count: int
    warning_count: int
    normal_count: int
    max_daily_avg: float
    affected_points: List[dict] = field(default_factory=list)


def get_assessment_for_cap(assessment_id: int) -> Optional[AssessmentForCAP]:
    """Query gha.expert_assessments for the data needed to create a CAP alert."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, expert_type, assessment_date, valid_from, valid_to,
                   country_code, country_name, risk_level, assessment_comment,
                   affected_areas, recommendations
            FROM gha.expert_assessments
            WHERE id = %s AND COALESCE(is_published, FALSE) = TRUE
        """, [assessment_id])
        row = cursor.fetchone()
        if not row:
            return None

    return AssessmentForCAP(
        assessment_id=row[0],
        expert_type=row[1] or "",
        assessment_date=row[2],
        valid_from=row[3],
        valid_to=row[4],
        country_code=row[5] or "",
        country_name=row[6] or "",
        risk_level=row[7] or "normal",
        assessment_comment=row[8] or "",
        affected_areas=row[9] or "",
        recommendations=row[10] or "",
    )


def get_forecast_alerts_for_cap(
    country_code: Optional[str] = None,
    min_level: str = "warning",
) -> List[ForecastAlertForCAP]:
    """
    Query multimodal forecast data and return per-country alert summaries.

    Uses the same 300/500/750 thresholds as the API.
    Only returns countries with at least one point at min_level or above.
    """
    min_threshold = {
        "warning": WARNING_THRESHOLD,
        "alarm": ALARM_THRESHOLD,
        "emergency": EMERGENCY_THRESHOLD,
    }.get(min_level, WARNING_THRESHOLD)

    country_filter = ""
    params = []
    if country_code:
        country_filter = "AND UPPER(cp.country_code) = UPPER(%s)"
        params.append(country_code)

    with connection.cursor() as cursor:
        cursor.execute(f"""
            WITH latest AS (
                SELECT MAX(data_date) as data_date FROM gha.multimodal_forecasts
            ),
            -- For each point, find the peak daily_avg across all forecast dates
            point_peak AS (
                SELECT
                    cp.point_id,
                    cp.country_code,
                    l.data_date,
                    MAX(COALESCE(f.daily_avg, 0)) as peak_daily_avg,
                    -- forecast_date where peak occurs
                    (ARRAY_AGG(f.forecast_date ORDER BY COALESCE(f.daily_avg, 0) DESC))[1] as peak_forecast_date
                FROM gha.multimodal_control_points cp
                CROSS JOIN latest l
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = l.data_date
                    AND f.forecast_date >= l.data_date
                WHERE 1=1 {country_filter}
                GROUP BY cp.point_id, cp.country_code, l.data_date
            ),
            point_alerts AS (
                SELECT
                    point_id,
                    country_code,
                    data_date,
                    peak_daily_avg as daily_avg,
                    peak_forecast_date as forecast_date,
                    CASE
                        WHEN peak_daily_avg >= {EMERGENCY_THRESHOLD} THEN 'emergency'
                        WHEN peak_daily_avg >= {ALARM_THRESHOLD} THEN 'alarm'
                        WHEN peak_daily_avg >= {WARNING_THRESHOLD} THEN 'warning'
                        ELSE 'normal'
                    END as alert_level
                FROM point_peak
            )
            SELECT
                country_code,
                MAX(data_date) as data_date,
                MAX(forecast_date) as forecast_date,
                COUNT(*) as total_points,
                SUM(CASE WHEN alert_level = 'emergency' THEN 1 ELSE 0 END) as emergency_count,
                SUM(CASE WHEN alert_level = 'alarm' THEN 1 ELSE 0 END) as alarm_count,
                SUM(CASE WHEN alert_level = 'warning' THEN 1 ELSE 0 END) as warning_count,
                SUM(CASE WHEN alert_level = 'normal' THEN 1 ELSE 0 END) as normal_count,
                MAX(daily_avg) as max_daily_avg
            FROM point_alerts
            GROUP BY country_code
            HAVING MAX(daily_avg) >= %s
            ORDER BY max_daily_avg DESC
        """, params + [min_threshold])

        rows = cursor.fetchall()

    # Map ISO-2 codes to country names
    country_names = _get_country_names()

    results = []
    for row in rows:
        cc = (row[0] or "").upper()
        iso3 = _iso2_to_iso3(cc)
        results.append(ForecastAlertForCAP(
            country_code=cc,
            country_code_iso3=iso3,
            country_name=country_names.get(cc, cc),
            data_date=row[1],
            forecast_date=row[2],
            total_points=row[3],
            emergency_count=row[4],
            alarm_count=row[5],
            warning_count=row[6],
            normal_count=row[7],
            max_daily_avg=float(row[8] or 0),
            risk_level=_highest_level(row[4], row[5], row[6]),
        ))

    return results


def _highest_level(emergency: int, alarm: int, warning: int) -> str:
    if emergency > 0:
        return "emergency"
    if alarm > 0:
        return "alarm"
    if warning > 0:
        return "warning"
    return "normal"


def _iso2_to_iso3(iso2: str) -> str:
    reverse = {v: k for k, v in ISO3_TO_ISO2.items()}
    return reverse.get(iso2.upper(), iso2)


def _get_country_names() -> dict:
    """Fetch country name mapping from gha.admin0."""
    names = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT gid_0, country FROM gha.admin0")
        for row in cursor.fetchall():
            iso2 = ISO3_TO_ISO2.get(row[0], row[0])
            names[iso2] = row[1]
    return names
