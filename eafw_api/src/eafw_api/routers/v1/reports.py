"""
FloodWatch Reports Router
Server-side PDF generation for flood analysis reports

Author: Hillary Koros
Organization: ICPAC
"""
import base64
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from eafw_api.db import get_connection
from eafw_api.routers.v1._helpers import format_report_key

logger = logging.getLogger(__name__)

router = APIRouter()

# Alert thresholds (consistent with multimodal-config)
DEFAULT_WARNING_THRESHOLD = 300.0
DEFAULT_ALARM_THRESHOLD = 500.0
DEFAULT_EMERGENCY_THRESHOLD = 750.0

# Country name mapping
COUNTRY_NAMES = {
    "BI": "Burundi",
    "DJ": "Djibouti",
    "ER": "Eritrea",
    "ET": "Ethiopia",
    "KE": "Kenya",
    "RW": "Rwanda",
    "SO": "Somalia",
    "SS": "South Sudan",
    "SD": "Sudan",
    "TZ": "Tanzania",
    "UG": "Uganda",
}

# Templates directory (eafw_api/src/eafw_api/templates)
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


class PdfRequest(BaseModel):
    """Request body for PDF generation."""

    forecast_date: str = Field(..., description="Forecast date YYYY-MM-DD")
    placename: str = Field(default="East Africa Region", description="Region/area name")
    unit_id: Optional[str] = Field(default=None, description="Admin unit ID")
    admin_level: Optional[str] = Field(default=None, description="Admin level")
    assessment_id: Optional[int] = Field(default=None, description="Assessment ID for interactive draft/published export")
    map_image: Optional[str] = Field(default=None, description="Base64 PNG of map screenshot")
    chart_image: Optional[str] = Field(default=None, description="Base64 PNG of chart screenshot")


async def _fetch_situation_data(conn, query_date):
    """Fetch situation summary data from the database."""
    # Spatial join to get country code
    point_country_sql = """
        COALESCE(
            (SELECT a0.gid_0 FROM gha.admin0 a0
             WHERE ST_Contains(a0.geom, cp.geom) LIMIT 1),
            UPPER(LEFT(cp.admin_name, 2))
        )
    """

    row = await conn.fetchrow(f"""
        WITH query_params AS (
            SELECT $1::date as query_date
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
                ({point_country_sql}) as country_code,
                COALESCE(f.daily_avg, 0) as daily_avg
            FROM gha.multimodal_control_points cp
            CROSS JOIN query_params qp
            CROSS JOIN first_forecast ff
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = qp.query_date
                AND f.forecast_date = ff.forecast_date
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
        )
        SELECT
            (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'emergency') as emergency_count,
            (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'alarm') as alarm_count,
            (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'warning') as warning_count,
            (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'normal') as normal_count,
            (SELECT COUNT(*) FROM risk_levels) as total_points
    """, query_date)

    # Country breakdown
    country_rows = await conn.fetch(f"""
        WITH query_params AS (
            SELECT $1::date as query_date
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
                ({point_country_sql}) as country_code,
                COALESCE(f.daily_avg, 0) as daily_avg
            FROM gha.multimodal_control_points cp
            CROSS JOIN query_params qp
            CROSS JOIN first_forecast ff
            LEFT JOIN gha.multimodal_forecasts f
                ON f.point_id = cp.point_id
                AND f.data_date = qp.query_date
                AND f.forecast_date = ff.forecast_date
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
            SUM(CASE WHEN risk_level = 'normal' THEN 1 ELSE 0 END) as normal,
            COUNT(*) as total
        FROM risk_levels
        GROUP BY country_code
        HAVING SUM(CASE WHEN risk_level IN ('emergency', 'alarm', 'warning') THEN 1 ELSE 0 END) > 0
        ORDER BY
            SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) DESC,
            SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) DESC
    """, query_date)

    risk_counts = {
        "emergency": row["emergency_count"] or 0,
        "alarm": row["alarm_count"] or 0,
        "warning": row["warning_count"] or 0,
        "normal": row["normal_count"] or 0,
        "total": row["total_points"] or 0,
    } if row else {"emergency": 0, "alarm": 0, "warning": 0, "normal": 0, "total": 0}

    countries = []
    for c_row in country_rows:
        code = c_row["country_code"]
        if code and len(code) == 2 and code.isalpha():
            countries.append({
                "code": code,
                "name": COUNTRY_NAMES.get(code, code),
                "emergency": c_row["emergency"] or 0,
                "alarm": c_row["alarm"] or 0,
                "warning": c_row["warning"] or 0,
                "normal": c_row["normal"] or 0,
            })

    return risk_counts, countries


@router.post("/flood-analysis/pdf")
async def generate_flood_analysis_pdf(data: PdfRequest):
    """
    Generate a professional PDF report for flood analysis.
    Accepts optional base64-encoded map and chart screenshots from the frontend.
    Returns a downloadable PDF.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
        from weasyprint import HTML
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation dependencies not available: {e}",
        )

    assessment_row = None
    interactive_report = None

    async with get_connection() as conn:
        if data.assessment_id:
            assessment_row = await conn.fetchrow(
                """
                SELECT id, expert_type, assessment_date, country_code, country_name, risk_level,
                       assessment_comment, affected_areas, recommendations, is_published
                FROM gha.expert_assessments
                WHERE id = $1
                """,
                data.assessment_id,
            )
            if not assessment_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Assessment {data.assessment_id} not found",
                )
            query_date = assessment_row["assessment_date"]
        else:
            try:
                query_date = datetime.strptime(data.forecast_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

        has_data = await conn.fetchval(
            "SELECT 1 FROM gha.multimodal_forecasts WHERE data_date = $1::date LIMIT 1",
            query_date,
        )
        if has_data:
            risk_counts, country_breakdown = await _fetch_situation_data(conn, query_date)
        else:
            if not data.assessment_id:
                raise HTTPException(
                    status_code=404,
                    detail=f"No forecast data available for date {query_date.isoformat()}",
                )
            risk_counts = {"emergency": 0, "alarm": 0, "warning": 0, "normal": 0, "total": 0}
            country_breakdown = []

        if assessment_row:
            assessment_country_code = (assessment_row["country_code"] or "REGION").upper()
            assessment_country_name = (
                assessment_row["country_name"]
                or COUNTRY_NAMES.get(assessment_country_code, assessment_country_code)
            )

            district_params = [assessment_row["expert_type"], assessment_row["assessment_date"]]
            district_query = """
                SELECT country, admin1, admin2, gid_2, risk_level, comment
                FROM gha.district_risk_levels
                WHERE expert_type = $1 AND assessment_date = $2
            """

            if assessment_country_code == "REGION":
                district_query += " AND UPPER(COALESCE(country, '')) LIKE 'REGION::%'"
            else:
                district_query += " AND (UPPER(COALESCE(country, '')) = $3 OR LOWER(COALESCE(country, '')) = LOWER($4))"
                district_params.extend([assessment_country_code, assessment_country_name])

            district_query += " ORDER BY country, admin1, admin2"
            district_rows = await conn.fetch(district_query, *district_params)

            district_summary = {"emergency": 0, "alarm": 0, "warning": 0, "watch": 0, "normal": 0}
            district_assessments = []
            for row in district_rows:
                district_country = row["country"]
                if district_country and district_country.startswith("REGION::"):
                    district_country = district_country.split("REGION::", 1)[1]

                district_risk = (row["risk_level"] or "normal").strip().lower()
                if district_risk in district_summary:
                    district_summary[district_risk] += 1

                district_assessments.append(
                    {
                        "country": district_country or "",
                        "admin1": row["admin1"] or "",
                        "admin2": row["admin2"] or "",
                        "gid_2": row["gid_2"] or "",
                        "risk_level": district_risk,
                        "comment": row["comment"] or "",
                    }
                )

            is_published = bool(assessment_row["is_published"])
            has_content = bool(
                (assessment_row["assessment_comment"] or "").strip()
                or (assessment_row["affected_areas"] or "").strip()
                or (assessment_row["recommendations"] or "").strip()
                or district_assessments
            )
            completion_state = "approved" if is_published else ("unapproved" if has_content else "unfinished")
            interactive_report = {
                "id": assessment_row["id"],
                "report_key": format_report_key(
                    assessment_row["expert_type"],
                    assessment_country_code,
                    assessment_row["assessment_date"].isoformat(),
                ),
                "status": "published" if is_published else "draft",
                "status_label": "Approved / Published" if is_published else "Draft / Unapproved",
                "completion_state": completion_state,
                "expert_type": assessment_row["expert_type"],
                "country_code": assessment_country_code,
                "country_name": assessment_country_name,
                "assessment_date": assessment_row["assessment_date"].isoformat(),
                "risk_level": (assessment_row["risk_level"] or "normal").strip().lower(),
                "assessment_comment": assessment_row["assessment_comment"] or "",
                "affected_areas": assessment_row["affected_areas"] or "",
                "recommendations": assessment_row["recommendations"] or "",
                "district_assessments": district_assessments,
                "district_summary": district_summary,
                "district_count": len(district_assessments),
            }

    # Determine overall alert level
    if risk_counts["emergency"] > 0:
        overall_level = "emergency"
    elif risk_counts["alarm"] > 0:
        overall_level = "alarm"
    elif risk_counts["warning"] > 0:
        overall_level = "warning"
    else:
        overall_level = "normal"

    # Calculate percentages
    total = risk_counts["total"] or 1
    risk_pcts = {k: round(v / total * 100, 1) for k, v in risk_counts.items() if k != "total"}

    # Prepare template context
    generated_at = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
    report_placename = (
        interactive_report["country_name"]
        if interactive_report and interactive_report.get("country_name")
        else data.placename
    )

    context = {
        "title": f"Flood Forecast Report for {report_placename}",
        "placename": report_placename,
        "forecast_date": query_date.strftime("%d %B %Y"),
        "forecast_date_iso": query_date.isoformat(),
        "generated_at": generated_at,
        "overall_level": overall_level,
        "risk_counts": risk_counts,
        "risk_pcts": risk_pcts,
        "country_breakdown": country_breakdown,
        "thresholds": {
            "warning": DEFAULT_WARNING_THRESHOLD,
            "alarm": DEFAULT_ALARM_THRESHOLD,
            "emergency": DEFAULT_EMERGENCY_THRESHOLD,
        },
        "map_image": data.map_image,
        "chart_image": data.chart_image,
        "interactive_report": interactive_report,
    }

    # Render HTML from Jinja2 template
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("flood_report.html")
    html_content = template.render(**context)

    # Generate PDF with WeasyPrint
    pdf_buffer = io.BytesIO()
    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    # Generate filename
    date_str = query_date.isoformat()
    region_str = report_placename.replace(" ", "_")
    filename = f"FloodAnalysis_{region_str}_{date_str}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
