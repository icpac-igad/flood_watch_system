"""
Forecasts API - Multimodal flood forecasts
Access to gha.multimodal_forecasts and control points
"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Query, HTTPException

from eafw_api.db import get_connection

router = APIRouter()


@router.get("/control-points")
async def list_control_points(
    zone: Optional[int] = Query(None, description="Filter by zone"),
    is_node: Optional[bool] = Query(None, description="Filter by is_node status"),
    whca_selected: Optional[bool] = Query(None, description="Filter by WHCA selection"),
    limit: int = Query(100, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List multimodal forecast control points.
    """
    async with get_connection() as conn:
        count_query = "SELECT COUNT(*) FROM gha.multimodal_control_points WHERE 1=1"
        query = """
            SELECT point_id, gridcode, admin_name, x, y, zone,
                   is_node, whca_selected, hybas_id, main_bas, coord_id,
                   ST_AsGeoJSON(geom)::json as geometry
            FROM gha.multimodal_control_points
            WHERE 1=1
        """
        params = []
        param_idx = 1

        if zone is not None:
            count_query += f" AND zone = ${param_idx}"
            query += f" AND zone = ${param_idx}"
            params.append(zone)
            param_idx += 1

        if is_node is not None:
            count_query += f" AND is_node = ${param_idx}"
            query += f" AND is_node = ${param_idx}"
            params.append(is_node)
            param_idx += 1

        if whca_selected is not None:
            count_query += f" AND whca_selected = ${param_idx}"
            query += f" AND whca_selected = ${param_idx}"
            params.append(whca_selected)
            param_idx += 1

        query += f" ORDER BY point_id LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])

        count_params = params[:-2] if len(params) > 2 else []
        total = await conn.fetchval(count_query, *count_params)
        rows = await conn.fetch(query, *params)

        features = [
            {
                "type": "Feature",
                "properties": {
                    "point_id": row["point_id"],
                    "gridcode": row["gridcode"],
                    "admin_name": row["admin_name"],
                    "zone": row["zone"],
                    "is_node": row["is_node"],
                    "whca_selected": row["whca_selected"],
                    "hybas_id": row["hybas_id"],
                    "coord_id": row["coord_id"],
                },
                "geometry": row["geometry"],
            }
            for row in rows
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "total": total,
            "count": len(features),
            "limit": limit,
            "offset": offset,
        }


@router.get("/control-points/{point_id}")
async def get_control_point(point_id: int):
    """Get a specific control point by ID."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT point_id, gridcode, admin_name, x, y, zone,
                   is_node, whca_selected, hybas_id, main_bas, coord_id,
                   ST_AsGeoJSON(geom)::json as geometry
            FROM gha.multimodal_control_points
            WHERE point_id = $1
            """,
            point_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Control point not found")

        return {
            "type": "Feature",
            "properties": {
                "point_id": row["point_id"],
                "gridcode": row["gridcode"],
                "admin_name": row["admin_name"],
                "x": row["x"],
                "y": row["y"],
                "zone": row["zone"],
                "is_node": row["is_node"],
                "whca_selected": row["whca_selected"],
                "hybas_id": row["hybas_id"],
                "coord_id": row["coord_id"],
            },
            "geometry": row["geometry"],
        }


@router.get("/data")
async def list_forecasts(
    forecast_date: Optional[date] = Query(None, description="Filter by forecast date"),
    point_id: Optional[int] = Query(None, description="Filter by control point"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    List multimodal forecast data.
    """
    async with get_connection() as conn:
        query = """
            SELECT f.*, cp.admin_name, cp.zone
            FROM gha.multimodal_forecasts f
            JOIN gha.multimodal_control_points cp ON f.point_id = cp.point_id
            WHERE 1=1
        """
        params = []
        param_idx = 1

        if forecast_date:
            query += f" AND f.forecast_date = ${param_idx}"
            params.append(forecast_date)
            param_idx += 1

        if point_id:
            query += f" AND f.point_id = ${param_idx}"
            params.append(point_id)
            param_idx += 1

        query += f" ORDER BY f.forecast_date DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

        forecasts = [dict(row) for row in rows]

        return {
            "forecasts": forecasts,
            "count": len(forecasts),
            "limit": limit,
            "offset": offset,
        }


@router.get("/data/{point_id}/timeseries")
async def get_point_timeseries(
    point_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(365, le=1000),
):
    """
    Get forecast timeseries for a specific control point.
    """
    async with get_connection() as conn:
        query = """
            SELECT *
            FROM gha.multimodal_forecasts
            WHERE point_id = $1
        """
        params = [point_id]
        param_idx = 2

        if start_date:
            query += f" AND forecast_date >= ${param_idx}"
            params.append(start_date)
            param_idx += 1

        if end_date:
            query += f" AND forecast_date <= ${param_idx}"
            params.append(end_date)
            param_idx += 1

        query += f" ORDER BY forecast_date DESC LIMIT ${param_idx}"
        params.append(limit)

        rows = await conn.fetch(query, *params)

        return {
            "point_id": point_id,
            "timeseries": [dict(row) for row in rows],
            "count": len(rows),
        }


@router.get("/available-dates")
async def get_available_dates(
    limit: int = Query(30, le=365, description="Number of recent dates"),
):
    """
    Get list of available forecast dates.
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT forecast_date, COUNT(*) as point_count
            FROM gha.multimodal_forecasts
            GROUP BY forecast_date
            ORDER BY forecast_date DESC
            LIMIT $1
            """,
            limit,
        )

        return {
            "dates": [
                {
                    "date": row["forecast_date"].isoformat() if row["forecast_date"] else None,
                    "point_count": row["point_count"],
                }
                for row in rows
            ],
            "count": len(rows),
        }
