"""
HydroBasins API - Watershed basin data for map filtering
Serves level 6 HydroSHEDS basin list with bounds for the watershed filter UI.

Author: Hillary Koros, ICPAC
"""
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from eafw_api.db import get_connection

router = APIRouter()


async def _resolve_hydrobasins_table(conn) -> str:
    """
    Resolve the HydroBASINS level-06 table name for the active DB.
    Supports both legacy and newer naming schemes.
    """
    rows = await conn.fetch("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'gha'
          AND table_name IN ('hydrobasins_lev06', 'hydrobasins_level06')
    """)
    names = {row["table_name"] for row in rows}

    if "hydrobasins_lev06" in names:
        return "gha.hydrobasins_lev06"
    if "hydrobasins_level06" in names:
        return "gha.hydrobasins_level06"

    raise HTTPException(
        status_code=500,
        detail="HydroBASINS level-06 table not found (expected gha.hydrobasins_lev06 or gha.hydrobasins_level06)",
    )


@router.get("/list")
async def get_basins(
    level: int = Query(6, description="HydroBASINS level (default 6)"),
    with_points: bool = Query(False, description="Only return basins that have forecast points"),
):
    """
    List all HydroBASINS at a given level with bounding boxes.
    Used by the watershed filter dropdown.
    """
    async with get_connection() as conn:
        basins_table = await _resolve_hydrobasins_table(conn)

        points_filter = ""
        if with_points:
            points_filter = """
                AND hb.hybas_id IN (
                    SELECT DISTINCT hybas_id FROM gha.multimodal_control_points WHERE hybas_id IS NOT NULL
                )
            """

        rows = await conn.fetch(f"""
            SELECT
                hb.hybas_id,
                hb.main_bas,
                hb.pfaf_id,
                hb.basin_order,
                hb.sub_area,
                hb.up_area,
                (SELECT count(*) FROM gha.multimodal_control_points cp WHERE cp.hybas_id = hb.hybas_id) as point_count,
                ST_XMin(ST_Envelope(hb.geom)) as west,
                ST_YMin(ST_Envelope(hb.geom)) as south,
                ST_XMax(ST_Envelope(hb.geom)) as east,
                ST_YMax(ST_Envelope(hb.geom)) as north
            FROM {basins_table} hb
            WHERE 1=1 {points_filter}
            ORDER BY hb.up_area DESC
        """)

        basins = []
        for row in rows:
            basins.append({
                "hybas_id": row["hybas_id"],
                "main_bas": row["main_bas"],
                "pfaf_id": row["pfaf_id"],
                "order": row["basin_order"],
                "sub_area": float(row["sub_area"]) if row["sub_area"] else 0,
                "up_area": float(row["up_area"]) if row["up_area"] else 0,
                "point_count": row["point_count"] or 0,
                "bbox": {
                    "west": float(row["west"]),
                    "south": float(row["south"]),
                    "east": float(row["east"]),
                    "north": float(row["north"]),
                },
            })

        return {"count": len(basins), "basins": basins}


@router.get("/{hybas_id}")
async def get_basin_geometry(hybas_id: int):
    """
    Get a single basin's geometry as a GeoJSON Feature with bbox.
    Used by BasinLayer to render basin boundary on the map.
    """
    async with get_connection() as conn:
        basins_table = await _resolve_hydrobasins_table(conn)
        row = await conn.fetchrow(f"""
            SELECT
                hb.hybas_id,
                ST_AsGeoJSON(hb.geom) as geometry,
                ST_XMin(ST_Envelope(hb.geom)) as west,
                ST_YMin(ST_Envelope(hb.geom)) as south,
                ST_XMax(ST_Envelope(hb.geom)) as east,
                ST_YMax(ST_Envelope(hb.geom)) as north
            FROM {basins_table} hb
            WHERE hb.hybas_id = $1
        """, hybas_id)

        if not row:
            raise HTTPException(status_code=404, detail=f"Basin {hybas_id} not found")

        # Parse geometry from GeoJSON string to dict
        geometry = json.loads(row["geometry"]) if isinstance(row["geometry"], str) else row["geometry"]

        feature = {
            "type": "Feature",
            "properties": {"hybas_id": row["hybas_id"]},
            "geometry": geometry,
            "bbox": [
                float(row["west"]),
                float(row["south"]),
                float(row["east"]),
                float(row["north"]),
            ],
        }

        return JSONResponse(content=feature)
