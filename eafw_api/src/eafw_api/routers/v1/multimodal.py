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
from ._helpers import (
    resolve_filter_geometry_ewkt,
    WHCA_SCOPE_SQL_CONDITION as _HELPERS_WHCA_SCOPE_SQL_CONDITION,
)

router = APIRouter()

# Default thresholds (same as CMS defaults)
DEFAULT_WARNING_THRESHOLD = 300.0
DEFAULT_ALARM_THRESHOLD = 500.0
DEFAULT_EMERGENCY_THRESHOLD = 750.0

# Country name to ISO code mapping
COUNTRY_CODES = {
    'ethiopia': 'ET', 'kenya': 'KE', 'uganda': 'UG',
    'sudan': 'SD', 'south sudan': 'SS', 'tanzania': 'TZ',
    'rwanda': 'RW', 'burundi': 'BI', 'somalia': 'SO', 'zanzibar': 'TZ',
    'djibouti': 'DJ', 'eritrea': 'ER'
}

COUNTRY_CODE_ALIASES = {
    "BD": "BI", "BDI": "BI",
    "DJI": "DJ",
    "ERI": "ER",
    "ETH": "ET",
    "KEN": "KE",
    "RWA": "RW",
    "SOM": "SO",
    "SSD": "SS",
    "SDN": "SD",
    "TZA": "TZ",
    "UGA": "UG",
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

# ISO3→ISO2 mapping for ST_Within fallback (admin0.gid_0 is ISO3)
ADMIN0_COUNTRY_CODE_SQL = (
    "CASE UPPER(TRIM(COALESCE(a0.gid_0, ''))) "
    "WHEN 'ETH' THEN 'ET' WHEN 'KEN' THEN 'KE' WHEN 'UGA' THEN 'UG' "
    "WHEN 'SDN' THEN 'SD' WHEN 'SSD' THEN 'SS' WHEN 'TZA' THEN 'TZ' "
    "WHEN 'RWA' THEN 'RW' WHEN 'BDI' THEN 'BI' WHEN 'SOM' THEN 'SO' "
    "WHEN 'DJI' THEN 'DJ' WHEN 'ERI' THEN 'ER' "
    "ELSE 'UN' END"
)

# Country code: use pre-populated cp.country_code (set via ST_Within),
# with spatial fallback for any new points not yet tagged.
POINT_COUNTRY_CODE_SQL = (
    "COALESCE("
    "NULLIF(UPPER(TRIM(cp.country_code)), ''), "
    f"(SELECT {ADMIN0_COUNTRY_CODE_SQL} FROM gha.admin0 a0 "
    "WHERE ST_Within(cp.geom, a0.geom) LIMIT 1), "
    "'UN')"
)
# Use the unified condition from _helpers (includes country-code fallback)
WHCA_SCOPE_SQL_CONDITION = _HELPERS_WHCA_SCOPE_SQL_CONDITION


def _build_project_country_filter(project_countries_csv):
    """Build a SQL condition from comma-separated ISO-3 or ISO-2 country codes.

    Returns a SQL fragment like:
        (COALESCE(...) IN ('ET','SD','UG'))
    filtering control points to the specified countries.
    Returns empty string if no valid codes provided.
    """
    if not project_countries_csv:
        return ""
    codes = [c.strip().upper() for c in project_countries_csv.split(",") if c.strip()]
    if not codes:
        return ""
    # Normalize ISO-3 to ISO-2 where possible
    iso2_codes = []
    for code in codes:
        alias = COUNTRY_CODE_ALIASES.get(code)
        if alias:
            iso2_codes.append(alias)
        elif len(code) == 2 and code.isalpha():
            iso2_codes.append(code)
        # Skip unrecognized codes
    if not iso2_codes:
        return ""
    codes_sql = ",".join(f"'{c}'" for c in iso2_codes)
    return f"({POINT_COUNTRY_CODE_SQL}) IN ({codes_sql})"


def _normalize_country_code(country: Optional[str]) -> Optional[str]:
    if not country:
        return None

    value = country.strip()
    if not value:
        return None

    mapped = COUNTRY_CODES.get(value.lower())
    if mapped:
        return mapped

    upper_value = value.upper()
    alias = COUNTRY_CODE_ALIASES.get(upper_value)
    if alias:
        return alias
    if len(upper_value) == 2 and upper_value.isalpha():
        return upper_value

    return None


@router.get("/geojson")
async def get_multimodal_geojson(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to latest)"),
    filter: Optional[str] = Query("all", description="Filter: all, active, alarm, emergency"),
    scope: Optional[str] = Query("all", description="Scope: all, whca, project"),
    country: Optional[str] = Query(None, description="Country name or ISO2 code"),
    country_name: Optional[str] = Query(None, description="Admin0 country name filter"),
    region_name: Optional[str] = Query(None, description="Admin1 region name filter"),
    district_name: Optional[str] = Query(None, description="Admin2 district name filter"),
    project_countries: Optional[str] = Query(None, description="Comma-separated project country names"),
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

    if scope not in ("all", "whca", "project"):
        raise HTTPException(status_code=400, detail="Invalid scope. Use all, whca, or project")

    country_name = (country_name or "").strip()
    region_name = (region_name or "").strip()
    district_name = (district_name or "").strip()
    project_countries = (project_countries or "").strip()
    project_country_list = [c.strip() for c in project_countries.split(",") if c.strip()] if project_countries else []
    # When scope=project, filtering is by country code (fast), not spatial geometry.
    # Only trigger spatial geometry for admin-level filters (country_name, region, district).
    use_project_code_filter = scope == "project" and project_country_list
    has_spatial_filter = bool(country_name or region_name or district_name or (project_country_list and not use_project_code_filter))

    # Backward-compatible country filter from legacy `country` query param.
    # If `country_name` is provided, it takes precedence for country-code filtering too.
    country_lookup_value = country_name or country
    country_code = _normalize_country_code(country_lookup_value)
    if country and not _normalize_country_code(country):
        raise HTTPException(status_code=400, detail="Invalid country. Use country name or ISO2 code")

    point_filters = []
    if scope == "whca":
        point_filters.append(WHCA_SCOPE_SQL_CONDITION)
    elif use_project_code_filter:
        pc_filter = _build_project_country_filter(",".join(project_country_list))
        if pc_filter:
            point_filters.append(pc_filter)
    if country_code:
        point_filters.append(f"({POINT_COUNTRY_CODE_SQL}) = '{country_code}'")

    async with get_connection() as conn:
        point_filter_params = []

        # Resolve clipping geometry once per request to avoid expensive per-row calls.
        if has_spatial_filter:
            clip_geom_ewkt = await resolve_filter_geometry_ewkt(
                conn,
                country_name=country_name,
                region_name=region_name,
                district_name=district_name,
                project_countries=project_country_list,
            )

            # If a spatial filter was requested but no matching geometry exists,
            # return an empty collection rather than silently dropping the filter.
            if not clip_geom_ewkt:
                return {"type": "FeatureCollection", "features": []}

            point_filters.append(f"ST_Within(cp.geom, ST_GeomFromEWKT(${len(point_filter_params) + 1}))")
            point_filter_params.append(clip_geom_ewkt)

        point_where_sql = ""
        if point_filters:
            point_where_sql = f"WHERE {' AND '.join(point_filters)}"

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
                    ({POINT_COUNTRY_CODE_SQL}) as country_code,
                    cp.whca_selected,
                    cp.hybas_id,
                    cp.geom,
                    f.data_date,
                    f.forecast_date,
                    COALESCE(f.daily_avg, 0) as daily_avg,
                    CASE
                        WHEN COALESCE(f.daily_avg, 0) >= {DEFAULT_EMERGENCY_THRESHOLD} THEN 'emergency'
                        WHEN COALESCE(f.daily_avg, 0) >= {DEFAULT_ALARM_THRESHOLD} THEN 'alarm'
                        WHEN COALESCE(f.daily_avg, 0) >= {DEFAULT_WARNING_THRESHOLD} THEN 'warning'
                        ELSE 'normal'
                    END as alert_level,
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
                {point_where_sql}
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
                            'alert_level', alert_level,
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

        if point_filter_params:
            row = await conn.fetchrow(query, *point_filter_params)
        else:
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
    scope: Optional[str] = Query("all", description="Scope: all, whca, project"),
    project_countries: Optional[str] = Query(None, description="Comma-separated ISO-3/ISO-2 country codes for project scope filtering"),
):
    """
    Get country summary with alert counts and bounds for homepage mini-map.
    Used by the "Regional Flood Situation" widget.
    """
    async with get_connection() as conn:
        if scope not in ("all", "whca", "project"):
            raise HTTPException(status_code=400, detail="Invalid scope. Use all, whca, or project")

        scope_sql = ""
        if scope == "whca":
            scope_sql = f"WHERE {WHCA_SCOPE_SQL_CONDITION}"
        elif scope == "project" and project_countries:
            pc_filter = _build_project_country_filter(project_countries)
            if pc_filter:
                scope_sql = f"WHERE {pc_filter}"

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
                    ({POINT_COUNTRY_CODE_SQL}) as country_code,
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
                    country_code,
                    MIN(ST_XMin(ST_Envelope(geom))) as west,
                    MIN(ST_YMin(ST_Envelope(geom))) as south,
                    MAX(ST_XMax(ST_Envelope(geom))) as east,
                    MAX(ST_YMax(ST_Envelope(geom))) as north
                FROM (
                    SELECT
                        {ADMIN0_COUNTRY_CODE_SQL} as country_code,
                        a0.geom
                    FROM gha.admin0 a0
                    WHERE a0.geom IS NOT NULL
                ) country_polygons
                WHERE country_code != 'UN'
                GROUP BY country_code
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
    scope: Optional[str] = Query("all", description="Scope: all, whca, project"),
    country: Optional[str] = Query(None, description="Country name or ISO2 code"),
    project_countries: Optional[str] = Query(None, description="Comma-separated ISO-3/ISO-2 country codes for project scope filtering"),
):
    """
    Get situation summary for homepage KPIs and ticker.
    Returns risk counts, peak forecast info, and country breakdown.
    """
    async with get_connection() as conn:
        requested_date = date_str or forecast_date
        if scope not in ("all", "whca", "project"):
            raise HTTPException(status_code=400, detail="Invalid scope. Use all, whca, or project")

        scope_where_sql = ""
        if scope == "whca":
            scope_where_sql = f" AND {WHCA_SCOPE_SQL_CONDITION}"
        elif scope == "project" and project_countries:
            pc_filter = _build_project_country_filter(project_countries)
            if pc_filter:
                scope_where_sql = f" AND {pc_filter}"

        country_code = _normalize_country_code(country)
        if country and not country_code:
            raise HTTPException(status_code=400, detail="Invalid country. Use country name or ISO2 code")

        country_where_sql = ""
        if country_code:
            country_where_sql = f" AND ({POINT_COUNTRY_CODE_SQL}) = '{country_code}'"

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
                    ({POINT_COUNTRY_CODE_SQL}) as country_code,
                    COALESCE(f.daily_avg, 0) as daily_avg
                FROM gha.multimodal_control_points cp
                CROSS JOIN query_params qp
                CROSS JOIN first_forecast ff
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = qp.query_date
                    AND f.forecast_date = ff.forecast_date
                WHERE 1=1 {scope_where_sql} {country_where_sql}
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
                {scope_where_sql} {country_where_sql}
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
                    ({POINT_COUNTRY_CODE_SQL}) as country_code,
                    COALESCE(f.daily_avg, 0) as daily_avg
                FROM gha.multimodal_control_points cp
                CROSS JOIN query_params qp
                CROSS JOIN first_forecast ff
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id
                    AND f.data_date = qp.query_date
                    AND f.forecast_date = ff.forecast_date
                WHERE 1=1 {scope_where_sql} {country_where_sql}
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


@router.get("/model-behavior")
async def get_model_behavior_timeseries(
    date: Optional[str] = Query(None, description="Reference run date YYYY-MM-DD (defaults to latest run)"),
    country: Optional[str] = Query(None, description="Country name or ISO2 code"),
    point_id: Optional[int] = Query(None, ge=1, description="Optional control point ID"),
    lead: int = Query(1, ge=1, le=14, description="Fixed lead time in days for historical comparison"),
    history_days: int = Query(90, ge=7, le=730, description="Historical window in days ending on reference date"),
    forecast_horizon_days: int = Query(14, ge=1, le=30, description="Horizon days for latest-run forecast series"),
    scope: Optional[str] = Query("all", description="Scope: all, whca, project"),
):
    """
    Fixed-lead model behavior comparison for flood-analysis reports.

    Returns two separate series:
    1) historical_behavior: fixed lead-time values per target date
    2) current_forecast: latest-run forecast values (separate from historical)
    """
    if scope not in ("all", "whca", "project"):
        raise HTTPException(status_code=400, detail="Invalid scope. Use all, whca, or project")

    country_code = _normalize_country_code(country)
    if country and not country_code:
        raise HTTPException(status_code=400, detail=f"Invalid country value: {country}")

    if date:
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") from exc
    else:
        query_date = None

    async with get_connection() as conn:
        if query_date is None:
            query_date = await conn.fetchval("SELECT MAX(data_date) FROM gha.multimodal_forecasts")
            if not query_date:
                raise HTTPException(status_code=404, detail="No forecast data available")
        else:
            has_date = await conn.fetchval(
                "SELECT 1 FROM gha.multimodal_forecasts WHERE data_date = $1::date LIMIT 1",
                query_date,
            )
            if not has_date:
                raise HTTPException(
                    status_code=404,
                    detail=f"No forecast data available for date {query_date.isoformat()}",
                )

        point_conditions = []
        params = []
        param_idx = 1

        if scope == "whca":
            point_conditions.append(WHCA_SCOPE_SQL_CONDITION)

        if point_id is not None:
            point_conditions.append(f"cp.point_id = ${param_idx}")
            params.append(point_id)
            param_idx += 1

        if country_code:
            point_conditions.append(f"{POINT_COUNTRY_CODE_SQL} = ${param_idx}")
            params.append(country_code)
            param_idx += 1

        point_where = f"WHERE {' AND '.join(point_conditions)}" if point_conditions else ""

        query_date_param = param_idx
        params.append(query_date)
        param_idx += 1

        lead_param = param_idx
        params.append(lead)
        param_idx += 1

        history_param = param_idx
        params.append(history_days)
        param_idx += 1

        horizon_param = param_idx
        params.append(forecast_horizon_days)

        row = await conn.fetchrow(
            f"""
            WITH selected_points AS (
                SELECT cp.point_id
                FROM gha.multimodal_control_points cp
                {point_where}
            ),
            historical AS (
                SELECT
                    mf.forecast_date::date AS target_date,
                    AVG(mf.daily_avg) AS daily_avg,
                    AVG(mf.geosfm) AS geosfm,
                    AVG(mf.floodproof) AS floodproof,
                    AVG(mf.mike_hydro_rfe) AS mike_hydro_rfe,
                    AVG(mf.mike_hydro_chirp) AS mike_hydro_chirp,
                    AVG(mf.mike_hydro_imerg) AS mike_hydro_imerg
                FROM gha.multimodal_forecasts mf
                JOIN selected_points sp ON sp.point_id = mf.point_id
                WHERE (mf.forecast_date - mf.data_date) = ${lead_param}
                  AND mf.forecast_date BETWEEN (
                        ${query_date_param}::date - (${history_param}::int - 1) * INTERVAL '1 day'
                  )::date AND ${query_date_param}::date
                GROUP BY mf.forecast_date
            ),
            latest_forecast AS (
                SELECT
                    mf.forecast_date::date AS target_date,
                    AVG(mf.daily_avg) AS daily_avg,
                    AVG(mf.geosfm) AS geosfm,
                    AVG(mf.floodproof) AS floodproof,
                    AVG(mf.mike_hydro_rfe) AS mike_hydro_rfe,
                    AVG(mf.mike_hydro_chirp) AS mike_hydro_chirp,
                    AVG(mf.mike_hydro_imerg) AS mike_hydro_imerg
                FROM gha.multimodal_forecasts mf
                JOIN selected_points sp ON sp.point_id = mf.point_id
                WHERE mf.data_date = ${query_date_param}::date
                  AND mf.forecast_date >= ${query_date_param}::date
                  AND mf.forecast_date < (
                        ${query_date_param}::date + ${horizon_param}::int * INTERVAL '1 day'
                  )::date
                GROUP BY mf.forecast_date
            )
            SELECT
                (SELECT COUNT(*) FROM selected_points) AS selected_points_count,
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'date', target_date::text,
                                'daily_avg', daily_avg,
                                'GeoSFM', geosfm,
                                'Floodproof', floodproof,
                                'Mike_Hydro_RFE', mike_hydro_rfe,
                                'Mike_Hydro_CHIRP', mike_hydro_chirp,
                                'Mike_Hydro_IMERG', mike_hydro_imerg
                            )
                            ORDER BY target_date
                        )
                        FROM historical
                    ),
                    '[]'::json
                ) AS historical_behavior,
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'date', target_date::text,
                                'daily_avg', daily_avg,
                                'GeoSFM', geosfm,
                                'Floodproof', floodproof,
                                'Mike_Hydro_RFE', mike_hydro_rfe,
                                'Mike_Hydro_CHIRP', mike_hydro_chirp,
                                'Mike_Hydro_IMERG', mike_hydro_imerg
                            )
                            ORDER BY target_date
                        )
                        FROM latest_forecast
                    ),
                    '[]'::json
                ) AS current_forecast
            """,
            *params,
        )

        historical_behavior = row["historical_behavior"] if row and row["historical_behavior"] is not None else []
        current_forecast = row["current_forecast"] if row and row["current_forecast"] is not None else []

        if isinstance(historical_behavior, str):
            historical_behavior = json.loads(historical_behavior)
        if isinstance(current_forecast, str):
            current_forecast = json.loads(current_forecast)

        selected_points_count = int(row["selected_points_count"] or 0) if row else 0

        return {
            "reference_date": query_date.isoformat(),
            "lead_time_days": lead,
            "history_days": history_days,
            "forecast_horizon_days": forecast_horizon_days,
            "country": country_code,
            "point_id": point_id,
            "scope": scope,
            "selected_points_count": selected_points_count,
            "historical_behavior": historical_behavior,
            "current_forecast": current_forecast,
            "thresholds": {
                "warning": DEFAULT_WARNING_THRESHOLD,
                "alarm": DEFAULT_ALARM_THRESHOLD,
                "emergency": DEFAULT_EMERGENCY_THRESHOLD,
            },
        }


@router.get("/grid-cells/")
async def get_grid_cells(
    country: str = Query(..., description="Country name"),
    region: str = Query(..., description="Region/admin1 name"),
):
    """
    Get 0.25 degree grid cells for a country/region from gha.grid_025dd.
    Used by the grid filter in the mapviewer.
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                xcol,
                yrow,
                centroid_lon,
                centroid_lat,
                ST_XMin(ST_Envelope(cell)) as bbox_left,
                ST_YMin(ST_Envelope(cell)) as bbox_bottom,
                ST_XMax(ST_Envelope(cell)) as bbox_right,
                ST_YMax(ST_Envelope(cell)) as bbox_top
            FROM gha.grid_025dd
            WHERE LOWER(admin0_name) = LOWER($1)
              AND LOWER(admin1_name) = LOWER($2)
            ORDER BY yrow, xcol
            """,
            country,
            region,
        )

        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "xcol": row["xcol"],
                "yrow": row["yrow"],
                "centroid_lon": float(row["centroid_lon"]) if row["centroid_lon"] is not None else None,
                "centroid_lat": float(row["centroid_lat"]) if row["centroid_lat"] is not None else None,
                "bbox": [
                    float(row["bbox_left"]) if row["bbox_left"] is not None else None,
                    float(row["bbox_bottom"]) if row["bbox_bottom"] is not None else None,
                    float(row["bbox_right"]) if row["bbox_right"] is not None else None,
                    float(row["bbox_top"]) if row["bbox_top"] is not None else None,
                ],
            })

        return results
