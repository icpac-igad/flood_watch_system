"""
Boundaries API - Admin boundaries from gha schema
Replaces DRF AdminBoundaryViewSet
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from eafw_api.db import get_connection

router = APIRouter()


@router.get("/countries")
async def list_countries():
    """
    List all countries (admin level 0).
    Equivalent to DRF AdminBoundaryViewSet.get()
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT gid_0, country
            FROM gha.admin0
            ORDER BY country
            """
        )

        countries = [
            {"gid_0": row["gid_0"], "country": row["country"]}
            for row in rows
        ]

        return {"countries": countries, "count": len(countries)}


@router.get("/countries/{gid_0}/regions")
async def list_regions(gid_0: str):
    """
    List regions (admin level 1) for a country.
    Equivalent to DRF AdminBoundaryViewSet.get_regions()
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT gid_0, country, gid_1, name_1
            FROM gha.admin1
            WHERE gid_0 = $1
            ORDER BY name_1
            """,
            gid_0,
        )

        if not rows:
            raise HTTPException(status_code=404, detail=f"No regions found for country {gid_0}")

        regions = [
            {
                "gid_0": row["gid_0"],
                "country": row["country"],
                "gid_1": row["gid_1"],
                "name_1": row["name_1"],
            }
            for row in rows
        ]

        return {"regions": regions, "count": len(regions)}


@router.get("/countries/{gid_0}/regions/{gid_1}/districts")
async def list_districts(gid_0: str, gid_1: str):
    """
    List districts (admin level 2) for a region.
    Equivalent to DRF AdminBoundaryViewSet.get_sub_regions()
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT gid_0, country, gid_1, name_1, gid_2, name_2
            FROM gha.admin2
            WHERE gid_0 = $1 AND gid_1 = $2
            ORDER BY name_2
            """,
            gid_0,
            gid_1,
        )

        if not rows:
            raise HTTPException(
                status_code=404, detail=f"No districts found for region {gid_1}"
            )

        districts = [
            {
                "gid_0": row["gid_0"],
                "country": row["country"],
                "gid_1": row["gid_1"],
                "name_1": row["name_1"],
                "gid_2": row["gid_2"],
                "name_2": row["name_2"],
            }
            for row in rows
        ]

        return {"districts": districts, "count": len(districts)}


@router.get("/admin0")
async def get_admin0_geojson(
    country: Optional[str] = Query(None, description="Filter by country code (gid_0)"),
):
    """
    Get admin0 boundaries as GeoJSON.
    """
    async with get_connection() as conn:
        query = """
            SELECT gid_0, country, ST_AsGeoJSON(geom)::json as geometry
            FROM gha.admin0
        """
        params = []

        if country:
            query += " WHERE gid_0 = $1"
            params.append(country)

        query += " ORDER BY country"

        rows = await conn.fetch(query, *params)

        features = [
            {
                "type": "Feature",
                "properties": {"gid_0": row["gid_0"], "country": row["country"]},
                "geometry": row["geometry"],
            }
            for row in rows
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "count": len(features),
        }


@router.get("/admin1")
async def get_admin1_geojson(
    country: Optional[str] = Query(None, description="Filter by country code (gid_0)"),
):
    """
    Get admin1 boundaries as GeoJSON.
    """
    async with get_connection() as conn:
        query = """
            SELECT gid_0, country, gid_1, name_1, ST_AsGeoJSON(geom)::json as geometry
            FROM gha.admin1
        """
        params = []

        if country:
            query += " WHERE gid_0 = $1"
            params.append(country)

        query += " ORDER BY country, name_1"

        rows = await conn.fetch(query, *params)

        features = [
            {
                "type": "Feature",
                "properties": {
                    "gid_0": row["gid_0"],
                    "country": row["country"],
                    "gid_1": row["gid_1"],
                    "name_1": row["name_1"],
                },
                "geometry": row["geometry"],
            }
            for row in rows
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "count": len(features),
        }


@router.get("/admin2")
async def get_admin2_geojson(
    country: Optional[str] = Query(None, description="Filter by country code (gid_0)"),
    region: Optional[str] = Query(None, description="Filter by region code (gid_1)"),
):
    """
    Get admin2 boundaries as GeoJSON.
    """
    async with get_connection() as conn:
        query = """
            SELECT gid_0, country, gid_1, name_1, gid_2, name_2,
                   ST_AsGeoJSON(geom)::json as geometry
            FROM gha.admin2
            WHERE 1=1
        """
        params = []
        param_idx = 1

        if country:
            query += f" AND gid_0 = ${param_idx}"
            params.append(country)
            param_idx += 1

        if region:
            query += f" AND gid_1 = ${param_idx}"
            params.append(region)
            param_idx += 1

        query += " ORDER BY country, name_1, name_2"

        rows = await conn.fetch(query, *params)

        features = [
            {
                "type": "Feature",
                "properties": {
                    "gid_0": row["gid_0"],
                    "country": row["country"],
                    "gid_1": row["gid_1"],
                    "name_1": row["name_1"],
                    "gid_2": row["gid_2"],
                    "name_2": row["name_2"],
                },
                "geometry": row["geometry"],
            }
            for row in rows
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "count": len(features),
        }


@router.get("/admin-boundaries/")
async def get_admin_boundaries_legacy(
    admin_level: Optional[str] = Query(None, description="None=countries, '0'=regions, '1'=districts"),
    unit_id: Optional[str] = Query(None, description="Parent unit name (country or region)"),
    with_bbox: Optional[str] = Query(None, description="Include bounding box ('true'/'false')"),
    country_id: Optional[str] = Query(None, description="Country name (for district queries)"),
):
    """
    Legacy-compatible admin-boundaries endpoint.
    Returns a flat JSON array matching the CMS AdminBoundaryView response format:
    [{code, name, bbox?}, ...]
    """
    include_bbox = with_bbox and with_bbox.lower() == "true"

    bbox_columns = ""
    if include_bbox:
        bbox_columns = """,
            ST_XMin(ST_Envelope(geom)) as left,
            ST_YMin(ST_Envelope(geom)) as bottom,
            ST_XMax(ST_Envelope(geom)) as right,
            ST_YMax(ST_Envelope(geom)) as top"""

    async with get_connection() as conn:
        if admin_level is None:
            # Countries
            rows = await conn.fetch(f"""
                SELECT DISTINCT country as code, country as name{bbox_columns}
                FROM gha.admin0
                WHERE country IS NOT NULL AND country != ''
                ORDER BY country
            """)

        elif admin_level == "0":
            # Regions (admin1) for a given country
            if not unit_id:
                return JSONResponse(content=[])
            rows = await conn.fetch(f"""
                SELECT DISTINCT name_1 as code, name_1 as name{bbox_columns}
                FROM gha.admin1
                WHERE country = $1 AND name_1 IS NOT NULL AND name_1 != ''
                ORDER BY name_1
            """, unit_id)

        elif admin_level == "1":
            # Districts (admin2) for a given region
            if not unit_id:
                return JSONResponse(content=[])

            if country_id:
                rows = await conn.fetch(f"""
                    SELECT DISTINCT name_2 as code, name_2 as name{bbox_columns}
                    FROM gha.admin2
                    WHERE country = $1 AND name_1 = $2
                        AND name_2 IS NOT NULL AND name_2 != ''
                    ORDER BY name_2
                """, country_id, unit_id)
            else:
                rows = await conn.fetch(f"""
                    SELECT DISTINCT name_2 as code, name_2 as name{bbox_columns}
                    FROM gha.admin2
                    WHERE name_1 = $1
                        AND name_2 IS NOT NULL AND name_2 != ''
                    ORDER BY name_2
                """, unit_id)

        else:
            return JSONResponse(content=[])

        results = []
        for row in rows:
            item = {"code": row["code"], "name": row["name"]}
            if include_bbox:
                item["bbox"] = {
                    "left": float(row["left"]),
                    "bottom": float(row["bottom"]),
                    "right": float(row["right"]),
                    "top": float(row["top"]),
                }
            results.append(item)

        return JSONResponse(content=results)
