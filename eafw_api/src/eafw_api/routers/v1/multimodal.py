"""
Multimodal Forecast API - Homepage widgets
Replaces DRF MultimodalForecastGeoJSONView, CountrySummaryWithBoundsView, SituationSummaryView

Author: Hillary Koros, ICPAC
"""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from eafw_api.db import get_connection

router = APIRouter()

# Default thresholds (same as CMS defaults)
DEFAULT_WARNING_THRESHOLD = 150.0
DEFAULT_ALARM_THRESHOLD = 300.0
DEFAULT_EMERGENCY_THRESHOLD = 450.0

# Country name to ISO code mapping
COUNTRY_CODES = {
    'ethiopia': 'ET', 'kenya': 'KE', 'uganda': 'UG',
    'sudan': 'SD', 'south sudan': 'SS', 'tanzania': 'TZ',
    'rwanda': 'RW', 'burundi': 'BI', 'somalia': 'SO', 'zanzibar': 'TZ',
    'djibouti': 'DJ', 'eritrea': 'ER'
}

COUNTRY_NAMES = {
    'ET': 'Ethiopia',
    'KE': 'Kenya',
    'UG': 'Uganda',
    'SD': 'Sudan',
    'SS': 'South Sudan',
    'TZ': 'Tanzania',
    'RW': 'Rwanda',
    'BI': 'Burundi',
    'SO': 'Somalia',
    'DJ': 'Djibouti',
    'ER': 'Eritrea',
    'UN': 'Unknown',
}

WHCA_COUNTRY_CODES = ("SD", "SS", "UG", "ET", "RW")
WHCA_COUNTRY_CODES_SQL = ",".join(f"'{code}'" for code in WHCA_COUNTRY_CODES)
WHCA_SCOPE_SQL_CONDITION = (
    "(COALESCE(cp.whca_selected, FALSE) IS TRUE OR "
    f"UPPER(COALESCE(cp.country_code, '')) IN ({WHCA_COUNTRY_CODES_SQL}))"
)


@router.get("/geojson")
async def get_multimodal_geojson(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to latest)"),
    filter: Optional[str] = Query("all", description="Filter: all, active, alarm, emergency"),
    scope: Optional[str] = Query("all", description="Scope: all, whca"),
):
    """
    Get multimodal ensemble forecast data as GeoJSON for map display.
    Uses normalized gha.multimodal_control_points and gha.multimodal_forecasts tables.
    """
    # Build filter SQL based on filter mode
    filter_sql = ""
    if filter == 'active':
        filter_sql = f"WHERE daily_avg >= {DEFAULT_WARNING_THRESHOLD}"
    elif filter == 'alarm':
        filter_sql = f"WHERE daily_avg >= {DEFAULT_ALARM_THRESHOLD}"
    elif filter == 'emergency':
        filter_sql = f"WHERE daily_avg >= {DEFAULT_EMERGENCY_THRESHOLD}"

    if scope not in ("all", "whca"):
        raise HTTPException(status_code=400, detail="Invalid scope. Use all or whca")

    scope_sql = ""
    if scope == "whca":
        scope_sql = f"WHERE {WHCA_SCOPE_SQL_CONDITION}"

    async with get_connection() as conn:
        # Determine query date
        if date:
            query_date_sql = f"'{date}'::date"
        else:
            query_date_sql = "(SELECT MAX(data_date) FROM gha.multimodal_forecasts)"

        query = f"""
            WITH query_params AS (
                SELECT {query_date_sql} as query_date
            ),
            first_forecast AS (
                SELECT MIN(forecast_date) as forecast_date
                FROM gha.multimodal_forecasts mf, query_params qp
                WHERE mf.data_date = qp.query_date
                  AND mf.forecast_date >= qp.query_date
            ),
            point_data AS (
                SELECT
                    cp.point_id,
                    cp.zone,
                    cp.gridcode,
                    cp.admin_name,
                    cp.country_code,
                    cp.whca_selected,
                    cp.hybas_id,
                    cp.geom,
                    f.data_date,
                    f.forecast_date,
                    COALESCE(f.daily_avg, 0) as daily_avg,
                    f.daily_max,
                    f.daily_min,
                    f.geosfm,
                    f.floodproof,
                    f.mike_hydro_rfe,
                    f.mike_hydro_chirp,
                    f.mike_hydro_imerg,
                    COALESCE((
                        SELECT json_agg(json_build_object(
                            'date', fc.forecast_date,
                            'daily_avg', fc.daily_avg,
                            'daily_max', fc.daily_max,
                            'daily_min', fc.daily_min,
                            'GeoSFM', fc.geosfm,
                            'Floodproof', fc.floodproof,
                            'Mike_Hydro_RFE', fc.mike_hydro_rfe,
                            'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
                            'Mike_Hydro_IMERG', fc.mike_hydro_imerg
                        ) ORDER BY fc.forecast_date)
                        FROM gha.multimodal_forecasts fc, query_params qp
                        WHERE fc.point_id = cp.point_id
                          AND fc.data_date = qp.query_date
                    ), '[]'::json) as forecasts
                FROM gha.multimodal_control_points cp
                CROSS JOIN query_params qp
                CROSS JOIN first_forecast ff
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = qp.query_date
                    AND f.forecast_date = ff.forecast_date
                {scope_sql}
            )
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(geom)::json,
                        'properties', json_build_object(
                            'point_id', point_id,
                            'zone', zone,
                            'gridcode', gridcode,
                            'admin_name', admin_name,
                            'country_code', country_code,
                            'whca_selected', whca_selected,
                            'hybas_id', hybas_id,
                            'data_date', data_date::text,
                            'forecast_date', forecast_date::text,
                            'daily_avg', daily_avg,
                            'daily_max', daily_max,
                            'daily_min', daily_min,
                            'geosfm', geosfm,
                            'floodproof', floodproof,
                            'mike_hydro_rfe', mike_hydro_rfe,
                            'mike_hydro_chirp', mike_hydro_chirp,
                            'mike_hydro_imerg', mike_hydro_imerg,
                            'forecasts', forecasts
                        )
                    )
                ), '[]'::json)
            ) as geojson
            FROM point_data
            {filter_sql}
        """

        row = await conn.fetchrow(query)

        if not row or not row['geojson']:
            raise HTTPException(status_code=404, detail="No forecast data available")

        geojson = row['geojson']
        # asyncpg can return json_build_object as a serialized string depending on codec config.
        if isinstance(geojson, str):
            try:
                geojson = json.loads(geojson)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=500, detail="Invalid GeoJSON payload") from exc

        return geojson


@router.get("/country-summary-with-bounds")
async def get_country_summary_with_bounds(
    scope: Optional[str] = Query("all", description="Scope: all, whca"),
):
    """
    Get country summary with alert counts and bounds for homepage mini-map.
    Used by the "Regional Flood Situation" widget.
    """
    async with get_connection() as conn:
        if scope not in ("all", "whca"):
            raise HTTPException(status_code=400, detail="Invalid scope. Use all or whca")

        scope_sql = ""
        if scope == "whca":
            scope_sql = f"WHERE {WHCA_SCOPE_SQL_CONDITION}"

        # Get latest data date
        latest_date = await conn.fetchval(
            "SELECT MAX(data_date) FROM gha.multimodal_forecasts"
        )

        if not latest_date:
            raise HTTPException(status_code=404, detail="No forecast data available")

        # Query country summary with bounds.
        # Uses cp.country_code (populated via ST_Within spatial join) for accurate country assignment.
        rows = await conn.fetch(f"""
            WITH query_params AS (
                SELECT '{latest_date}'::date as query_date
            ),
            first_forecast AS (
                SELECT MIN(forecast_date) as forecast_date
                FROM gha.multimodal_forecasts mf, query_params qp
                WHERE mf.data_date = qp.query_date
                  AND mf.forecast_date >= qp.query_date
            ),
            point_data AS (
                SELECT
                    cp.point_id,
                    cp.country_code,
                    COALESCE(f.daily_avg, 0) as daily_avg
                FROM gha.multimodal_control_points cp
                CROSS JOIN query_params qp
                CROSS JOIN first_forecast ff
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = qp.query_date
                    AND f.forecast_date = ff.forecast_date
                {scope_sql}
            ),
            point_risk AS (
                SELECT
                    point_id,
                    country_code,
                    daily_avg,
                    CASE
                        WHEN daily_avg >= {DEFAULT_EMERGENCY_THRESHOLD} THEN 'emergency'
                        WHEN daily_avg >= {DEFAULT_ALARM_THRESHOLD} THEN 'alarm'
                        WHEN daily_avg >= {DEFAULT_WARNING_THRESHOLD} THEN 'warning'
                        ELSE 'normal'
                    END as risk_level
                FROM point_data
            ),
            country_agg AS (
                SELECT
                    country_code,
                    SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) as emergency,
                    SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) as alarm,
                    SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as warning,
                    COUNT(*) as total_points,
                    SUM(CASE WHEN risk_level = 'emergency' THEN 100 ELSE 0 END) +
                    SUM(CASE WHEN risk_level = 'alarm' THEN 10 ELSE 0 END) +
                    SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as severity_score
                FROM point_risk
                GROUP BY country_code
            ),
            country_bounds AS (
                SELECT
                    cp.country_code,
                    MIN(ST_XMin(ST_Envelope(a0.geom))) as west,
                    MIN(ST_YMin(ST_Envelope(a0.geom))) as south,
                    MAX(ST_XMax(ST_Envelope(a0.geom))) as east,
                    MAX(ST_YMax(ST_Envelope(a0.geom))) as north
                FROM gha.admin0 a0
                JOIN (SELECT DISTINCT country_code FROM gha.multimodal_control_points) cp
                    ON cp.country_code = CASE
                        WHEN LOWER(a0.country) = 'ethiopia' THEN 'ET'
                        WHEN LOWER(a0.country) = 'kenya' THEN 'KE'
                        WHEN LOWER(a0.country) = 'uganda' THEN 'UG'
                        WHEN LOWER(a0.country) = 'sudan' THEN 'SD'
                        WHEN LOWER(a0.country) = 'south sudan' THEN 'SS'
                        WHEN LOWER(a0.country) IN ('tanzania', 'zanzibar') THEN 'TZ'
                        WHEN LOWER(a0.country) = 'rwanda' THEN 'RW'
                        WHEN LOWER(a0.country) = 'burundi' THEN 'BI'
                        WHEN LOWER(a0.country) = 'somalia' THEN 'SO'
                        WHEN LOWER(a0.country) = 'djibouti' THEN 'DJ'
                        WHEN LOWER(a0.country) = 'eritrea' THEN 'ER'
                        ELSE 'UN'
                    END
                GROUP BY cp.country_code
            )
            SELECT
                ca.country_code,
                ca.emergency,
                ca.alarm,
                ca.warning,
                ca.total_points,
                ca.severity_score,
                cb.west,
                cb.south,
                cb.east,
                cb.north
            FROM country_agg ca
            LEFT JOIN country_bounds cb ON cb.country_code = ca.country_code
            WHERE ca.emergency > 0 OR ca.alarm > 0 OR ca.warning > 0
            ORDER BY ca.severity_score DESC, ca.emergency DESC, ca.alarm DESC, ca.warning DESC
        """)

        countries = []
        for row in rows:
            code = row['country_code'] or 'UN'
            country_name = COUNTRY_NAMES.get(code, code)

            country_data = {
                'code': code,
                'name': country_name,
                'emergency': row['emergency'] or 0,
                'alarm': row['alarm'] or 0,
                'warning': row['warning'] or 0,
                'total_points': row['total_points'] or 0,
            }

            if row['west'] is not None:
                country_data['bounds'] = {
                    'west': float(row['west']),
                    'south': float(row['south']),
                    'east': float(row['east']),
                    'north': float(row['north'])
                }
            else:
                country_data['bounds'] = None

            countries.append(country_data)

        return {
            'data_date': latest_date.strftime('%Y-%m-%d') if hasattr(latest_date, 'strftime') else str(latest_date),
            'scope': scope,
            'countries': countries,
            'thresholds': {
                'warning': DEFAULT_WARNING_THRESHOLD,
                'alarm': DEFAULT_ALARM_THRESHOLD,
                'emergency': DEFAULT_EMERGENCY_THRESHOLD,
            }
        }


@router.get("/situation-summary")
async def get_situation_summary(
    horizon: int = Query(7, description="Days ahead for forecast horizon"),
    date_str: Optional[str] = Query(None, alias="date", description="Data date in YYYY-MM-DD format"),
    forecast_date: Optional[str] = Query(None, description="Alias for date"),
    scope: Optional[str] = Query("all", description="Scope: all, whca"),
):
    """
    Get situation summary for homepage KPIs and ticker.
    Returns risk counts, peak forecast info, and country breakdown.
    """
    async with get_connection() as conn:
        requested_date = date_str or forecast_date
        if scope not in ("all", "whca"):
            raise HTTPException(status_code=400, detail="Invalid scope. Use all or whca")

        scope_where_sql = ""
        if scope == "whca":
            scope_where_sql = f" AND {WHCA_SCOPE_SQL_CONDITION}"

        # Resolve query date (requested or latest available)
        if requested_date:
            try:
                query_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date format: {requested_date}. Expected YYYY-MM-DD.",
                ) from exc

            has_data = await conn.fetchval(
                "SELECT 1 FROM gha.multimodal_forecasts WHERE data_date = $1::date LIMIT 1",
                query_date,
            )
            if not has_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No forecast data available for date {requested_date}",
                )
        else:
            query_date = await conn.fetchval(
                "SELECT MAX(data_date) FROM gha.multimodal_forecasts"
            )
            if not query_date:
                raise HTTPException(status_code=404, detail="No forecast data available")

        # Get summary statistics
        row = await conn.fetchrow(f"""
            WITH query_params AS (
                SELECT '{query_date}'::date as query_date
            ),
            first_forecast AS (
                SELECT MIN(forecast_date) as forecast_date
                FROM gha.multimodal_forecasts mf, query_params qp
                WHERE mf.data_date = qp.query_date
                  AND mf.forecast_date >= qp.query_date
            ),
            point_data AS (
                SELECT
                    cp.point_id,
                    cp.country_code,
                    COALESCE(f.daily_avg, 0) as daily_avg
                FROM gha.multimodal_control_points cp
                CROSS JOIN query_params qp
                CROSS JOIN first_forecast ff
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = qp.query_date
                    AND f.forecast_date = ff.forecast_date
                WHERE 1=1 {scope_where_sql}
            ),
            risk_levels AS (
                SELECT
                    point_id,
                    country_code,
                    daily_avg,
                    CASE
                        WHEN daily_avg >= {DEFAULT_EMERGENCY_THRESHOLD} THEN 'emergency'
                        WHEN daily_avg >= {DEFAULT_ALARM_THRESHOLD} THEN 'alarm'
                        WHEN daily_avg >= {DEFAULT_WARNING_THRESHOLD} THEN 'warning'
                        ELSE 'normal'
                    END as risk_level
                FROM point_data
            ),
            risk_by_date AS (
                SELECT
                    mf.forecast_date,
                    CASE
                        WHEN mf.daily_avg >= {DEFAULT_EMERGENCY_THRESHOLD} THEN 'emergency'
                        WHEN mf.daily_avg >= {DEFAULT_ALARM_THRESHOLD} THEN 'alarm'
                        WHEN mf.daily_avg >= {DEFAULT_WARNING_THRESHOLD} THEN 'warning'
                        ELSE 'normal'
                    END as risk_level
                FROM gha.multimodal_forecasts mf
                JOIN gha.multimodal_control_points cp ON cp.point_id = mf.point_id
                CROSS JOIN query_params qp
                WHERE mf.data_date = qp.query_date
                {scope_where_sql}
            )
            SELECT
                (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'emergency') as emergency_count,
                (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'alarm') as alarm_count,
                (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'warning') as warning_count,
                (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'normal') as normal_count,
                (SELECT COUNT(*) FROM risk_levels) as total_points,
                (
                    SELECT forecast_date
                    FROM risk_by_date
                    WHERE risk_level IN ('emergency', 'alarm', 'warning')
                    GROUP BY forecast_date
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                ) as peak_day
        """)

        # Get country breakdown using spatial country_code
        country_rows = await conn.fetch(f"""
            WITH query_params AS (
                SELECT '{query_date}'::date as query_date
            ),
            first_forecast AS (
                SELECT MIN(forecast_date) as forecast_date
                FROM gha.multimodal_forecasts mf, query_params qp
                WHERE mf.data_date = qp.query_date
                  AND mf.forecast_date >= qp.query_date
            ),
            point_data AS (
                SELECT
                    cp.point_id,
                    cp.country_code,
                    COALESCE(f.daily_avg, 0) as daily_avg
                FROM gha.multimodal_control_points cp
                CROSS JOIN query_params qp
                CROSS JOIN first_forecast ff
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = qp.query_date
                    AND f.forecast_date = ff.forecast_date
                WHERE 1=1 {scope_where_sql}
            ),
            risk_levels AS (
                SELECT
                    point_id,
                    country_code,
                    CASE
                        WHEN daily_avg >= {DEFAULT_EMERGENCY_THRESHOLD} THEN 'emergency'
                        WHEN daily_avg >= {DEFAULT_ALARM_THRESHOLD} THEN 'alarm'
                        WHEN daily_avg >= {DEFAULT_WARNING_THRESHOLD} THEN 'warning'
                        ELSE 'normal'
                    END as risk_level
                FROM point_data
            )
            SELECT
                country_code,
                SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) as emergency,
                SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) as alarm,
                SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as warning,
                COUNT(*) as total
            FROM risk_levels
            WHERE risk_level != 'normal'
            GROUP BY country_code
            HAVING SUM(CASE WHEN risk_level IN ('emergency', 'alarm', 'warning') THEN 1 ELSE 0 END) > 0
            ORDER BY
                SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) DESC,
                SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) DESC,
                SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) DESC
        """)

        country_breakdown = []
        for c_row in country_rows:
            code = c_row['country_code']
            if code and len(code) == 2 and code.isalpha():
                country_breakdown.append({
                    'code': code,
                    'name': code,
                    'emergency': c_row['emergency'] or 0,
                    'alarm': c_row['alarm'] or 0,
                    'warning': c_row['warning'] or 0,
                    'total_at_risk': (c_row['emergency'] or 0) + (c_row['alarm'] or 0) + (c_row['warning'] or 0),
                })

        if row:
            summary = {
                'data_date': query_date.strftime('%Y-%m-%d') if hasattr(query_date, 'strftime') else str(query_date),
                'scope': scope,
                'horizon_days': horizon,
                'risk_counts': {
                    'emergency': row['emergency_count'] or 0,
                    'alarm': row['alarm_count'] or 0,
                    'warning': row['warning_count'] or 0,
                    'normal': row['normal_count'] or 0,
                    'total': row['total_points'] or 0,
                },
                'peak_day': str(row['peak_day']) if row['peak_day'] else None,
                'country_breakdown': country_breakdown,
                'thresholds': {
                    'warning': DEFAULT_WARNING_THRESHOLD,
                    'alarm': DEFAULT_ALARM_THRESHOLD,
                    'emergency': DEFAULT_EMERGENCY_THRESHOLD,
                }
            }
        else:
            summary = {
                'data_date': query_date.strftime('%Y-%m-%d') if hasattr(query_date, 'strftime') else str(query_date),
                'scope': scope,
                'horizon_days': horizon,
                'risk_counts': {
                    'emergency': 0,
                    'alarm': 0,
                    'warning': 0,
                    'normal': 0,
                    'total': 0,
                },
                'peak_day': None,
                'country_breakdown': [],
                'thresholds': {
                    'warning': DEFAULT_WARNING_THRESHOLD,
                    'alarm': DEFAULT_ALARM_THRESHOLD,
                    'emergency': DEFAULT_EMERGENCY_THRESHOLD,
                }
            }

        return summary


@router.get("/dates")
async def get_multimodal_available_dates(
    limit: int = Query(365, ge=1, le=2000, description="Maximum number of data dates to return"),
):
    """
    Get available multimodal data dates for date selectors.
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT data_date
            FROM gha.multimodal_forecasts
            ORDER BY data_date DESC
            LIMIT $1
            """,
            limit,
        )

        timestamps = [
            row["data_date"].isoformat()
            for row in rows
            if row["data_date"] is not None
        ]

        return {
            "timestamps": timestamps,
            "dates": timestamps,  # backward compatibility
            "count": len(timestamps),
        }
