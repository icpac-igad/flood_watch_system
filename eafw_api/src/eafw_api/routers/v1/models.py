"""
Model-specific GeoJSON API - GeoSFM, MikeHydro, Floodproof
Replaces CMS BaseModularModelGeoJSONView and subclasses.

Author: Hillary Koros, ICPAC
"""
import json
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from eafw_api.db import get_connection
from ._helpers import (
    DEFAULT_WARNING_THRESHOLD, DEFAULT_ALARM_THRESHOLD, DEFAULT_EMERGENCY_THRESHOLD,
    WHCA_SCOPE_SQL_CONDITION, resolve_filter_geometry_ewkt,
)

router = APIRouter()

# Model-specific SQL fragments
MODEL_CONFIGS = {
    "geosfm": {
        "current_value": lambda alias: f"{alias}.geosfm",
        "forecast_object": """json_build_object(
            'date', fc.forecast_date,
            'daily_avg', fc.geosfm,
            'GeoSFM', fc.geosfm
        )""",
        "endpoint_path": "/api/v1/models/geosfm/geojson/",
    },
    "mike-hydro": {
        "current_value": lambda alias: (
            f"(SELECT MAX(v) FROM (VALUES ({alias}.mike_hydro_rfe), "
            f"({alias}.mike_hydro_chirp), ({alias}.mike_hydro_imerg)) AS vals(v))"
        ),
        "forecast_object": """json_build_object(
            'date', fc.forecast_date,
            'daily_avg', (SELECT MAX(v) FROM (VALUES (fc.mike_hydro_rfe), (fc.mike_hydro_chirp), (fc.mike_hydro_imerg)) AS vals(v)),
            'Mike_Hydro_RFE', fc.mike_hydro_rfe,
            'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
            'Mike_Hydro_IMERG', fc.mike_hydro_imerg
        )""",
        "endpoint_path": "/api/v1/models/mike-hydro/geojson/",
    },
    "floodproof": {
        "current_value": lambda alias: f"{alias}.floodproof",
        "forecast_object": """json_build_object(
            'date', fc.forecast_date,
            'daily_avg', fc.floodproof,
            'Floodproof', fc.floodproof
        )""",
        "endpoint_path": "/api/v1/models/floodproof/geojson/",
    },
}


async def _model_geojson(
    model_key: str,
    date: Optional[str] = None,
    filter: str = "all",
    scope: str = "all",
    country_name: str = "",
    region_name: str = "",
    district_name: str = "",
    project_countries: str = "",
):
    """Shared implementation for model-specific GeoJSON endpoints."""
    cfg = MODEL_CONFIGS[model_key]
    current_value_mf = cfg["current_value"]("mf")
    current_value_f = cfg["current_value"]("f")
    current_value_fc = cfg["current_value"]("fc")
    forecast_object_sql = cfg["forecast_object"]
    endpoint_path = cfg["endpoint_path"]

    warning_threshold = DEFAULT_WARNING_THRESHOLD
    alarm_threshold = DEFAULT_ALARM_THRESHOLD
    emergency_threshold = DEFAULT_EMERGENCY_THRESHOLD

    filter_sql = ""
    if filter == "active":
        filter_sql = f"WHERE daily_avg >= {warning_threshold}"
    elif filter == "alarm":
        filter_sql = f"WHERE daily_avg >= {alarm_threshold}"
    elif filter == "emergency":
        filter_sql = f"WHERE daily_avg >= {emergency_threshold}"

    if scope not in ("all", "whca"):
        raise HTTPException(status_code=400, detail="Invalid scope. Use all or whca")

    proj_countries = [c.strip() for c in project_countries.split(",") if c.strip()] if project_countries else []

    async with get_connection() as conn:
        if date:
            query_date_sql = f"'{date}'::date"
        else:
            query_date_sql = "(SELECT MAX(data_date) FROM gha.multimodal_forecasts)"

        clip_geom_ewkt = await resolve_filter_geometry_ewkt(
            conn,
            country_name=country_name,
            region_name=region_name,
            district_name=district_name,
            project_countries=proj_countries,
        )

        point_filters = []
        if scope == "whca":
            point_filters.append(WHCA_SCOPE_SQL_CONDITION)
        if clip_geom_ewkt:
            point_filters.append(f"ST_Within(cp.geom, ST_GeomFromEWKT('{clip_geom_ewkt}'))")

        point_where_sql = f"WHERE {' AND '.join(point_filters)}" if point_filters else ""

        query = f"""
            WITH query_params AS (
                SELECT {query_date_sql} AS query_date
            ),
            first_forecast AS (
                SELECT mf.point_id, MIN(mf.forecast_date) AS forecast_date
                FROM gha.multimodal_forecasts mf, query_params qp
                WHERE mf.data_date = qp.query_date
                  AND mf.forecast_date >= qp.query_date
                  AND {current_value_mf} IS NOT NULL
                GROUP BY mf.point_id
            ),
            point_data AS (
                SELECT
                    cp.point_id, cp.zone, cp.gridcode, cp.admin_name,
                    cp.country_code, cp.whca_selected, cp.hybas_id, cp.geom,
                    f.data_date, f.forecast_date,
                    {current_value_f} AS daily_avg,
                    f.geosfm, f.floodproof,
                    f.mike_hydro_rfe, f.mike_hydro_chirp, f.mike_hydro_imerg,
                    COALESCE((
                        SELECT json_agg({forecast_object_sql} ORDER BY fc.forecast_date)
                        FROM gha.multimodal_forecasts fc, query_params qp
                        WHERE fc.point_id = cp.point_id
                          AND fc.data_date = qp.query_date
                          AND {current_value_fc} IS NOT NULL
                    ), '[]'::json) AS forecasts
                FROM gha.multimodal_control_points cp
                JOIN first_forecast ff ON ff.point_id = cp.point_id
                CROSS JOIN query_params qp
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
                            'geosfm', geosfm,
                            'floodproof', floodproof,
                            'mike_hydro_rfe', mike_hydro_rfe,
                            'mike_hydro_chirp', mike_hydro_chirp,
                            'mike_hydro_imerg', mike_hydro_imerg,
                            'threshold_alert', {warning_threshold},
                            'threshold_alarm', {alarm_threshold},
                            'threshold_emergency', {emergency_threshold},
                            'alert_level', CASE
                                WHEN daily_avg >= {emergency_threshold} THEN 'emergency'
                                WHEN daily_avg >= {alarm_threshold} THEN 'alarm'
                                WHEN daily_avg >= {warning_threshold} THEN 'warning'
                                ELSE 'normal'
                            END,
                            'data_endpoint', '{endpoint_path}',
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


@router.get("/geosfm/geojson")
async def get_geosfm_geojson(
    date: Optional[str] = Query(None),
    filter: str = Query("all"),
    scope: str = Query("all"),
    country_name: str = Query(""),
    region_name: str = Query(""),
    district_name: str = Query(""),
    project_countries: str = Query(""),
):
    """GeoSFM model-specific GeoJSON endpoint."""
    return await _model_geojson("geosfm", date, filter, scope, country_name, region_name, district_name, project_countries)


@router.get("/mike-hydro/geojson")
async def get_mike_hydro_geojson(
    date: Optional[str] = Query(None),
    filter: str = Query("all"),
    scope: str = Query("all"),
    country_name: str = Query(""),
    region_name: str = Query(""),
    district_name: str = Query(""),
    project_countries: str = Query(""),
):
    """MikeHydro model-specific GeoJSON endpoint."""
    return await _model_geojson("mike-hydro", date, filter, scope, country_name, region_name, district_name, project_countries)


@router.get("/floodproof/geojson")
async def get_floodproof_geojson(
    date: Optional[str] = Query(None),
    filter: str = Query("all"),
    scope: str = Query("all"),
    country_name: str = Query(""),
    region_name: str = Query(""),
    district_name: str = Query(""),
    project_countries: str = Query(""),
):
    """Floodproof model-specific GeoJSON endpoint."""
    return await _model_geojson("floodproof", date, filter, scope, country_name, region_name, district_name, project_countries)
