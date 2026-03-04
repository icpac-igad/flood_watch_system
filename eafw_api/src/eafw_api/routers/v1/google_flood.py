"""
Google Flood API - GeoJSON and available dates
Replaces CMS GoogleFloodGeoJSONView and GoogleFloodAvailableDatesView.

Author: Hillary Koros, ICPAC
"""
import json
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from eafw_api.db import get_connection
from ._helpers import resolve_filter_geometry_ewkt

router = APIRouter()


@router.get("/geojson")
async def get_google_flood_geojson(
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (defaults to latest)"),
    filter: str = Query("all", description="Filter: all, active, alarm, emergency"),
    scope: str = Query("all", description="Scope: all, whca, project"),
    confidence: str = Query("high", description="Confidence: all, high, low"),
    extended_coverage: str = Query("false", description="Include lower-confidence gauges"),
    country_name: str = Query(""),
    region_name: str = Query(""),
    district_name: str = Query(""),
    project_countries: str = Query(""),
):
    """Google Flood Hub synced data as GeoJSON."""
    confidence_mode = confidence.strip().lower()
    if confidence_mode not in ("all", "high", "low"):
        confidence_mode = "high"

    if extended_coverage.strip().lower() in ("1", "true", "yes", "on"):
        confidence_mode = "all"

    if scope not in ("all", "whca", "project"):
        raise HTTPException(status_code=400, detail="Invalid scope. Use all, whca, or project")

    filter_sql = ""
    if filter == "active":
        filter_sql = "WHERE alert_level != 'normal'"
    elif filter == "alarm":
        filter_sql = "WHERE alert_level IN ('alarm', 'emergency')"
    elif filter == "emergency":
        filter_sql = "WHERE alert_level = 'emergency'"

    proj_countries = [c.strip() for c in project_countries.split(",") if c.strip()] if project_countries else []

    async with get_connection() as conn:
        # Check table exists
        exists = await conn.fetchval("SELECT to_regclass('gha.google_flood_points_latest')")
        if not exists:
            return {"type": "FeatureCollection", "features": []}

        if date:
            query_date_sql = f"'{date}'::date"
        else:
            query_date_sql = "(SELECT MAX(data_date) FROM gha.google_flood_points_latest)"

        clip_geom_ewkt = await resolve_filter_geometry_ewkt(
            conn,
            country_name=country_name,
            region_name=region_name,
            district_name=district_name,
            project_countries=proj_countries,
        )

        scope_sql = ""
        if scope == "whca":
            scope_sql = (
                "AND UPPER(COALESCE(NULLIF(g.country_code, ''), NULLIF(g.region_code, ''), '')) "
                "IN ('SD','SS','UG','ET','RW')"
            )

        confidence_sql = ""
        if confidence_mode == "high":
            confidence_sql = "AND UPPER(COALESCE(g.confidence_level, '')) = 'HIGH'"
        elif confidence_mode == "low":
            confidence_sql = "AND UPPER(COALESCE(g.confidence_level, '')) = 'LOW'"

        spatial_clip_sql = ""
        if clip_geom_ewkt:
            spatial_clip_sql = f"AND ST_Within(g.geom, ST_GeomFromEWKT('{clip_geom_ewkt}'))"

        query = f"""
            WITH query_params AS (
                SELECT {query_date_sql} AS query_date
            ),
            point_data AS (
                SELECT
                    g.gauge_id,
                    COALESCE(NULLIF(g.point_id, ''), g.gauge_id) AS point_id,
                    COALESCE(NULLIF(g.admin_name, ''), NULLIF(g.site_name, ''), g.gauge_id) AS admin_name,
                    g.hybas_id,
                    COALESCE(NULLIF(g.country_code, ''), NULLIF(g.region_code, '')) AS country_code,
                    g.region_code,
                    g.data_date,
                    g.latest_issued_time AS forecast_date,
                    g.daily_avg, g.daily_max, g.daily_min,
                    g.threshold_alert, g.threshold_alarm, g.threshold_emergency,
                    g.latest_severity, g.latest_forecast_trend,
                    g.confidence_level, g.confidence_score,
                    g.quality_verified, g.model_quality_verified, g.status_quality_verified,
                    COALESCE(g.forecasts_json, '[]'::jsonb) AS forecasts,
                    CASE
                        -- Prefer explicit Google severity classes when provided.
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('EXTREME', 'EXTREME_FLOODING', 'MAJOR_FLOODING') THEN 'emergency'
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('SEVERE', 'DANGER', 'MODERATE_FLOODING') THEN 'alarm'
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('WARNING', 'WATCH', 'MINOR_FLOODING', 'ALERT') THEN 'warning'

                        -- Fallback to threshold-based classification using forecast discharge.
                        WHEN g.daily_max IS NOT NULL AND g.threshold_emergency IS NOT NULL AND g.daily_max >= g.threshold_emergency THEN 'emergency'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alarm IS NOT NULL AND g.daily_max >= g.threshold_alarm THEN 'alarm'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alert IS NOT NULL AND g.daily_max >= g.threshold_alert THEN 'warning'

                        WHEN g.daily_avg IS NOT NULL AND g.threshold_emergency IS NOT NULL AND g.daily_avg >= g.threshold_emergency THEN 'emergency'
                        WHEN g.daily_avg IS NOT NULL AND g.threshold_alarm IS NOT NULL AND g.daily_avg >= g.threshold_alarm THEN 'alarm'
                        WHEN g.daily_avg IS NOT NULL AND g.threshold_alert IS NOT NULL AND g.daily_avg >= g.threshold_alert THEN 'warning'
                        ELSE 'normal'
                    END AS alert_level,
                    g.geom
                FROM gha.google_flood_points_latest g
                CROSS JOIN query_params qp
                WHERE (qp.query_date IS NULL OR g.data_date = qp.query_date)
                  AND g.geom IS NOT NULL
                  {scope_sql}
                  {confidence_sql}
                  {spatial_clip_sql}
            )
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(geom)::json,
                        'properties', json_build_object(
                            'gauge_id', gauge_id,
                            'point_id', point_id,
                            'admin_name', admin_name,
                            'hybas_id', hybas_id,
                            'country_code', country_code,
                            'region_code', region_code,
                            'data_date', data_date::text,
                            'forecast_date', forecast_date::text,
                            'daily_avg', daily_avg,
                            'daily_max', daily_max,
                            'daily_min', daily_min,
                            'threshold_alert', threshold_alert,
                            'threshold_alarm', threshold_alarm,
                            'threshold_emergency', threshold_emergency,
                            'google_flood_severity', latest_severity,
                            'forecast_trend', latest_forecast_trend,
                            'confidence_level', confidence_level,
                            'confidence_score', confidence_score,
                            'quality_verified', quality_verified,
                            'model_quality_verified', model_quality_verified,
                            'status_quality_verified', status_quality_verified,
                            'extended_coverage', CASE
                                WHEN UPPER(COALESCE(confidence_level, '')) = 'LOW' THEN TRUE
                                ELSE FALSE
                            END,
                            'alert_level', alert_level,
                            'data_endpoint', '/api/v1/google-flood/geojson/',
                            'forecasts', forecasts
                        )
                    )
                ), '[]'::json)
            ) AS geojson
            FROM point_data
            {filter_sql}
        """

        row = await conn.fetchrow(query)
        if not row or not row["geojson"]:
            return {"type": "FeatureCollection", "features": []}

        geojson = row["geojson"]
        if isinstance(geojson, str):
            geojson = json.loads(geojson)
        return geojson


@router.get("/dates")
async def get_google_flood_dates():
    """Available synced dates for Google Flood data."""
    async with get_connection() as conn:
        exists = await conn.fetchval("SELECT to_regclass('gha.google_flood_points_latest')")
        if not exists:
            return {"timestamps": []}

        rows = await conn.fetch("""
            SELECT DISTINCT data_date
            FROM gha.google_flood_points_latest
            WHERE data_date IS NOT NULL
            ORDER BY data_date DESC
        """)

        timestamps = [row["data_date"].strftime("%Y-%m-%d") for row in rows]
        return {"timestamps": timestamps}
