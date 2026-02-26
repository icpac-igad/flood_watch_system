"""
Risk & Summary APIs - Forecast majority risk, river basins, regional summary, hotspots
Replaces CMS ForecastMajorityRiskView, RiverBasinsView, RegionalSummaryView, HotspotsView.

Author: Hillary Koros, ICPAC
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Request

from eafw_api.db import get_connection
from ._helpers import (
    DEFAULT_WARNING_THRESHOLD, DEFAULT_ALARM_THRESHOLD, DEFAULT_EMERGENCY_THRESHOLD,
    normalize_country_code, ISO2_TO_COUNTRY_NAME,
    WHCA_SCOPE_SQL_CONDITION,
)

router = APIRouter()


@router.get("/risk-majority")
async def get_forecast_majority_risk(
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD"),
    country: str = Query("", description="Country name or ISO2 code"),
    admin_level: str = Query("2", description="Admin level: 1 or 2"),
    scope: str = Query("all", description="Scope filter: all, whca"),
):
    """Majority flood risk by admin unit from forecast points."""
    if admin_level not in ("1", "2"):
        admin_level = "2"

    country_code = normalize_country_code(country)
    country_name = ISO2_TO_COUNTRY_NAME.get(country_code, country) if country_code else ""

    warning_threshold = DEFAULT_WARNING_THRESHOLD
    alarm_threshold = DEFAULT_ALARM_THRESHOLD
    emergency_threshold = DEFAULT_EMERGENCY_THRESHOLD

    async with get_connection() as conn:
        if date:
            try:
                query_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            query_date = await conn.fetchval("SELECT MAX(data_date) FROM gha.multimodal_forecasts")

        if not query_date:
            return {"risk_by_admin": [], "count": 0}

        country_filter_sql = ""
        params = [query_date]
        param_idx = 2
        if country_code and country_code != "REGION":
            country_filter_sql = f"AND (UPPER(COALESCE(ad.country, '')) = ${param_idx} OR LOWER(COALESCE(ad.country, '')) = LOWER(${param_idx + 1}))"
            params.extend([country_code, country_name or country])
            param_idx += 2

        admin_fields = (
            "ad.country, ad.name_1 as admin1, ad.name_2 as admin2, ad.gid_2 as gid_2"
            if admin_level == "2"
            else "ad.country, ad.name_1 as admin1, NULL::text as admin2, NULL::text as gid_2"
        )
        admin_group = "country, admin1, admin2, gid_2"
        admin_join_table = "gha.admin2" if admin_level == "2" else "gha.admin1"

        rows = await conn.fetch(f"""
            WITH query_params AS (
                SELECT $1::date as query_date
            ),
            first_forecast AS (
                SELECT MIN(forecast_date) as forecast_date
                FROM gha.multimodal_forecasts mf, query_params qp
                WHERE mf.data_date = qp.query_date AND mf.forecast_date >= qp.query_date
            ),
            points AS (
                SELECT cp.point_id, cp.geom, COALESCE(f.daily_avg, 0) as daily_avg
                FROM gha.multimodal_control_points cp
                CROSS JOIN query_params qp
                CROSS JOIN first_forecast ff
                LEFT JOIN gha.multimodal_forecasts f
                    ON f.point_id = cp.point_id AND f.data_date = qp.query_date AND f.forecast_date = ff.forecast_date
                {"WHERE " + WHCA_SCOPE_SQL_CONDITION if scope == "whca" else ""}
            ),
            risk_points AS (
                SELECT p.point_id, p.geom,
                    CASE
                        WHEN p.daily_avg >= {emergency_threshold} THEN 'emergency'
                        WHEN p.daily_avg >= {alarm_threshold} THEN 'alarm'
                        WHEN p.daily_avg >= {warning_threshold} THEN 'warning'
                        ELSE 'normal'
                    END as risk_level
                FROM points p
            ),
            point_admin AS (
                SELECT {admin_fields}, rp.risk_level
                FROM risk_points rp
                JOIN {admin_join_table} ad ON ST_Within(rp.geom, ad.geom)
                WHERE 1=1 {country_filter_sql}
            ),
            grouped AS (
                SELECT {admin_group}, risk_level, COUNT(*) as point_count
                FROM point_admin GROUP BY {admin_group}, risk_level
            ),
            ranked AS (
                SELECT g.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY {admin_group}
                        ORDER BY g.point_count DESC,
                            CASE WHEN g.risk_level = 'emergency' THEN 4
                                 WHEN g.risk_level = 'alarm' THEN 3
                                 WHEN g.risk_level = 'warning' THEN 2
                                 ELSE 1 END DESC
                    ) as rn
                FROM grouped g
            ),
            totals AS (
                SELECT {admin_group}, SUM(point_count) as total_points
                FROM grouped GROUP BY {admin_group}
            )
            SELECT r.country, r.admin1, r.admin2, r.gid_2, r.risk_level,
                   r.point_count as majority_points, t.total_points
            FROM ranked r
            JOIN totals t ON t.country = r.country AND t.admin1 = r.admin1
                AND (t.admin2 = r.admin2 OR (t.admin2 IS NULL AND r.admin2 IS NULL))
                AND (t.gid_2 = r.gid_2 OR (t.gid_2 IS NULL AND r.gid_2 IS NULL))
            WHERE r.rn = 1
            ORDER BY r.country, r.admin1, r.admin2
        """, *params)

        risk_by_admin = []
        for row in rows:
            item = {
                "country": row["country"],
                "admin1": row["admin1"],
                "admin2": row["admin2"],
                "gid_2": row["gid_2"],
                "risk_level": row["risk_level"],
                "majority_points": int(row["majority_points"] or 0),
                "total_points": int(row["total_points"] or 0),
            }
            if item["gid_2"]:
                item["key"] = item["gid_2"]
            elif item["admin2"]:
                item["key"] = f"{item['country']}-{item['admin1']}-{item['admin2']}"
            else:
                item["key"] = f"{item['country']}-{item['admin1']}"
            risk_by_admin.append(item)

        return {
            "date": query_date.strftime("%Y-%m-%d") if hasattr(query_date, "strftime") else str(query_date),
            "admin_level": admin_level,
            "risk_by_admin": risk_by_admin,
            "count": len(risk_by_admin),
        }


@router.get("/river-basins")
async def get_river_basins():
    """Major river basins in GHA region for filter dropdowns."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT main_bas as code,
                   CASE main_bas
                       WHEN 1060000010 THEN 'Nile Basin'
                       WHEN 1060013900 THEN 'Juba-Shabelle Basin'
                       WHEN 1060015050 THEN 'Omo-Turkana Basin'
                       WHEN 1060017830 THEN 'Tana Basin'
                       WHEN 1060016650 THEN 'Awash Basin'
                       WHEN 1060018330 THEN 'Rift Valley Lakes'
                       WHEN 1060019040 THEN 'Lake Victoria Basin'
                       ELSE 'Basin ' || main_bas
                   END as name,
                   ST_XMin(ST_Extent(geom)) as left,
                   ST_YMin(ST_Extent(geom)) as bottom,
                   ST_XMax(ST_Extent(geom)) as right,
                   ST_YMax(ST_Extent(geom)) as top
            FROM gha.hydrobasins_lev06
            GROUP BY main_bas
            ORDER BY name
        """)

        basins = []
        for row in rows:
            basins.append({
                "code": str(row["code"]),
                "name": row["name"],
                "bbox": {
                    "left": float(row["left"]) if row["left"] else None,
                    "bottom": float(row["bottom"]) if row["bottom"] else None,
                    "right": float(row["right"]) if row["right"] else None,
                    "top": float(row["top"]) if row["top"] else None,
                },
            })

        return basins


@router.post("/regional-summary/generate")
async def generate_regional_summary(request: Request):
    """Generate regional summary from country assessments."""
    data = await request.json()

    assessments = data.get("assessments", {})
    forecast_date = data.get("forecast_date")

    risk_priority = {"emergency": 5, "alarm": 4, "warning": 3, "watch": 2, "normal": 1}
    max_risk = "normal"
    max_priority = 1

    affected_areas = []
    recommendations = []
    comments = []

    for country_code, assessment in assessments.items():
        if not assessment:
            continue
        risk = assessment.get("risk_level", "normal")
        if risk_priority.get(risk, 1) > max_priority:
            max_priority = risk_priority[risk]
            max_risk = risk
        cname = assessment.get("country_name", country_code)
        if assessment.get("affected_areas"):
            affected_areas.append(f"**{cname}:** {assessment['affected_areas']}")
        if assessment.get("recommendations"):
            recommendations.append(f"**{cname}:** {assessment['recommendations']}")
        if assessment.get("comment"):
            comments.append(f"**{cname}:** {assessment['comment']}")

    summary = {
        "forecast_date": forecast_date,
        "overall_risk": max_risk,
        "affected_areas": "\n\n".join(affected_areas),
        "combined_recommendations": "\n\n".join(recommendations),
        "situation_summary": "\n\n".join(comments),
        "countries_reported": len([a for a in assessments.values() if a and a.get("comment")]),
        "generated_at": datetime.now().isoformat(),
    }

    return {"summary": summary}


@router.get("/hotspots")
async def get_hotspots(
    limit: int = Query(10, ge=1, le=100, description="Max hotspots to return"),
    scope: str = Query("all", description="Scope filter: all, whca"),
):
    """Ranked hotspots with highest flood risk for homepage table."""
    warning_threshold = 500
    alarm_threshold = 750
    emergency_threshold = 1500

    async with get_connection() as conn:
        latest_date = await conn.fetchval(
            "SELECT MAX(data_date) FROM home_multimodal_forecast_geojson"
        )
        if not latest_date:
            raise HTTPException(status_code=404, detail="No forecast data available")

        rows = await conn.fetch("""
            WITH latest_forecasts AS (
                SELECT jsonb_array_elements(geojson_data->'features') as feature
                FROM home_multimodal_forecast_geojson WHERE data_date = $1
            ),
            forecast_data AS (
                SELECT
                    feature->'properties'->>'point_id' as point_id,
                    feature->'properties'->>'admin_name' as admin_name,
                    feature->'properties'->'forecasts' as forecasts,
                    (feature->'geometry'->'coordinates'->0)::float as lon,
                    (feature->'geometry'->'coordinates'->1)::float as lat
                FROM latest_forecasts
                WHERE feature->'properties'->'forecasts' IS NOT NULL
                {f"AND (feature->'properties'->>'point_id')::int IN (SELECT cp.point_id FROM gha.multimodal_control_points cp WHERE {WHCA_SCOPE_SQL_CONDITION})" if scope == "whca" else ""}
            ),
            point_stats AS (
                SELECT point_id, admin_name, lon, lat,
                    MAX((f->>'daily_avg')::float) as max_discharge,
                    (SELECT f2->>'date' FROM jsonb_array_elements(forecasts) f2
                     ORDER BY (f2->>'daily_avg')::float DESC LIMIT 1) as peak_date
                FROM forecast_data, jsonb_array_elements(forecasts) f
                GROUP BY point_id, admin_name, lon, lat, forecasts
            ),
            ranked_points AS (
                SELECT *, CASE
                    WHEN max_discharge >= $2 THEN 'emergency'
                    WHEN max_discharge >= $3 THEN 'alarm'
                    WHEN max_discharge >= $4 THEN 'warning'
                    ELSE 'normal'
                END as risk_level,
                CASE
                    WHEN max_discharge >= $2 THEN 3
                    WHEN max_discharge >= $3 THEN 2
                    WHEN max_discharge >= $4 THEN 1
                    ELSE 0
                END as risk_score
                FROM point_stats
            )
            SELECT point_id, admin_name, lon, lat,
                   ROUND(max_discharge::numeric, 1) as max_discharge,
                   peak_date, risk_level
            FROM ranked_points
            WHERE risk_level != 'normal'
            ORDER BY risk_score DESC, max_discharge DESC
            LIMIT $5
        """, latest_date, emergency_threshold, alarm_threshold, warning_threshold, limit)

        hotspots = []
        for i, row in enumerate(rows, 1):
            hotspots.append({
                "rank": i,
                "point_id": row["point_id"],
                "admin_name": row["admin_name"] or "No Admin",
                "lon": row["lon"],
                "lat": row["lat"],
                "max_discharge": float(row["max_discharge"]) if row["max_discharge"] else None,
                "peak_date": row["peak_date"],
                "risk_level": row["risk_level"],
            })

        # Get daily forecast values for each hotspot
        if hotspots:
            point_ids = [h["point_id"] for h in hotspots]
            daily_rows = await conn.fetch("""
                WITH latest_forecasts AS (
                    SELECT jsonb_array_elements(geojson_data->'features') as feature
                    FROM home_multimodal_forecast_geojson WHERE data_date = $1
                ),
                point_forecasts AS (
                    SELECT feature->'properties'->>'point_id' as point_id,
                           feature->'properties'->'forecasts' as forecasts
                    FROM latest_forecasts
                    WHERE feature->'properties'->>'point_id' = ANY($2)
                )
                SELECT point_id,
                    jsonb_agg(
                        jsonb_build_object('date', f->>'date', 'discharge', ROUND((f->>'daily_avg')::numeric, 0))
                        ORDER BY f->>'date'
                    ) as daily_values
                FROM point_forecasts, jsonb_array_elements(forecasts) f
                GROUP BY point_id
            """, latest_date, point_ids)

            daily_data = {row["point_id"]: row["daily_values"] for row in daily_rows}
            for h in hotspots:
                h["daily_values"] = daily_data.get(h["point_id"], [])

        return {
            "data_date": latest_date.strftime("%Y-%m-%d"),
            "hotspots": hotspots,
            "count": len(hotspots),
            "thresholds": {
                "warning": warning_threshold,
                "alarm": alarm_threshold,
                "emergency": emergency_threshold,
            },
        }
