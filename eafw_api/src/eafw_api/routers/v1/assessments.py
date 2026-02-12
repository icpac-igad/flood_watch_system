"""
Expert Assessments API - FloodWatch specific
For hydrologists and meteorologists risk assessments
"""
import json
from typing import Optional, Literal
from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel, Field

from eafw_api.db import get_connection
from ._helpers import (
    normalize_country_code, ISO2_TO_COUNTRY_NAME,
    coerce_bool, parse_creator_metadata, format_report_key,
)

router = APIRouter()


def _parse_assessment_date_or_400(raw_value, field_name="assessment_date"):
    if not raw_value:
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    if isinstance(raw_value, date):
        return raw_value
    text = str(raw_value).strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}. Use YYYY-MM-DD",
        ) from exc


# Pydantic models for request/response
class ExpertAssessmentCreate(BaseModel):
    expert_type: Literal["hydrologist", "meteorologist"]
    assessment_date: date
    country_code: str = Field(default="REGION", max_length=10)
    country_name: Optional[str] = Field(default="East Africa Region", max_length=100)
    risk_level: Literal["normal", "watch", "warning", "alarm", "emergency"] = "normal"
    assessment_comment: str = Field(..., min_length=10, description="Required assessment comment")
    affected_areas: Optional[str] = None
    recommendations: Optional[str] = None
    created_by: Optional[str] = None


class ExpertAssessmentResponse(BaseModel):
    id: int
    expert_type: str
    assessment_date: date
    country_code: str
    country_name: Optional[str]
    risk_level: str
    assessment_comment: str
    affected_areas: Optional[str]
    recommendations: Optional[str]
    created_by: Optional[str]
    is_published: bool
    created_at: Optional[str]
    updated_at: Optional[str]


class DistrictRiskCreate(BaseModel):
    expert_type: Literal["hydrologist", "meteorologist"]
    assessment_date: date
    country: str
    admin1: str
    admin2: str
    gid_2: Optional[str] = None
    risk_level: Literal["normal", "watch", "warning", "alarm", "emergency"] = "normal"
    comment: Optional[str] = None


@router.get("/expert")
async def list_expert_assessments(
    assessment_date: Optional[date] = Query(None, description="Filter by date"),
    expert_type: Optional[Literal["hydrologist", "meteorologist"]] = Query(None),
    country_code: Optional[str] = Query(None, description="Filter by country code"),
    published_only: bool = Query(False, description="Only return published assessments"),
):
    """
    List expert assessments.
    Replaces DRF CountryAssessmentsView.get()
    """
    async with get_connection() as conn:
        query = """
            SELECT id, expert_type, assessment_date, valid_from, valid_to,
                   country_code, country_name, risk_level, assessment_comment,
                   affected_areas, recommendations, created_by,
                   created_at::text, updated_at::text, is_published
            FROM gha.expert_assessments
            WHERE 1=1
        """
        params = []
        param_idx = 1

        if assessment_date:
            query += f" AND assessment_date = ${param_idx}"
            params.append(assessment_date)
            param_idx += 1

        if expert_type:
            query += f" AND expert_type = ${param_idx}"
            params.append(expert_type)
            param_idx += 1

        if country_code:
            query += f" AND country_code = ${param_idx}"
            params.append(country_code)
            param_idx += 1

        if published_only:
            query += " AND is_published = TRUE"

        query += " ORDER BY assessment_date DESC, country_name"

        rows = await conn.fetch(query, *params)

        assessments = [dict(row) for row in rows]

        return {
            "assessments": assessments,
            "count": len(assessments),
        }


@router.post("/expert", status_code=201)
async def create_expert_assessment(data: ExpertAssessmentCreate):
    """
    Create or update expert assessment.
    Replaces DRF CountryAssessmentsView.post()
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO gha.expert_assessments
                (expert_type, assessment_date, country_code, country_name,
                 risk_level, assessment_comment, affected_areas, recommendations,
                 created_by, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_TIMESTAMP)
            ON CONFLICT (expert_type, assessment_date, country_code)
            DO UPDATE SET
                risk_level = EXCLUDED.risk_level,
                assessment_comment = EXCLUDED.assessment_comment,
                affected_areas = EXCLUDED.affected_areas,
                recommendations = EXCLUDED.recommendations,
                country_name = EXCLUDED.country_name,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            data.expert_type,
            data.assessment_date,
            data.country_code,
            data.country_name,
            data.risk_level,
            data.assessment_comment,
            data.affected_areas,
            data.recommendations,
            data.created_by,
        )

        return {
            "success": True,
            "id": row["id"],
            "message": "Expert assessment saved successfully",
        }


@router.get("/expert/{assessment_id}")
async def get_expert_assessment(assessment_id: int):
    """Get a specific expert assessment by ID."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, expert_type, assessment_date, valid_from, valid_to,
                   country_code, country_name, risk_level, assessment_comment,
                   affected_areas, recommendations, created_by,
                   created_at::text, updated_at::text, is_published
            FROM gha.expert_assessments
            WHERE id = $1
            """,
            assessment_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Assessment not found")

        return dict(row)


@router.patch("/expert/{assessment_id}/publish")
async def publish_assessment(assessment_id: int):
    """Publish an expert assessment."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            UPDATE gha.expert_assessments
            SET is_published = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id
            """,
            assessment_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Assessment not found")

        return {"success": True, "message": "Assessment published"}


# District-level risk assessments
@router.get("/districts")
async def list_district_risks(
    assessment_date: Optional[date] = Query(None),
    expert_type: Optional[Literal["hydrologist", "meteorologist"]] = Query(None),
    country: Optional[str] = Query(None),
):
    """
    List district-level risk assessments.
    Replaces DRF RiskAssessmentView.get()
    """
    async with get_connection() as conn:
        query = """
            SELECT id, expert_type, assessment_date, country, admin1, admin2,
                   gid_2, risk_level, comment, created_at::text, updated_at::text
            FROM gha.district_risk_levels
            WHERE 1=1
        """
        params = []
        param_idx = 1

        if assessment_date:
            query += f" AND assessment_date = ${param_idx}"
            params.append(assessment_date)
            param_idx += 1

        if expert_type:
            query += f" AND expert_type = ${param_idx}"
            params.append(expert_type)
            param_idx += 1

        if country:
            query += f" AND country = ${param_idx}"
            params.append(country)
            param_idx += 1

        query += " ORDER BY country, admin1, admin2"

        rows = await conn.fetch(query, *params)

        return {
            "assessments": [dict(row) for row in rows],
            "count": len(rows),
        }


@router.post("/districts", status_code=201)
async def create_district_risk(data: DistrictRiskCreate):
    """
    Create or update district risk level.
    Replaces DRF RiskAssessmentView.post()
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO gha.district_risk_levels
                (expert_type, assessment_date, country, admin1, admin2, gid_2,
                 risk_level, comment, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
            ON CONFLICT (expert_type, assessment_date, country, admin1, admin2)
            DO UPDATE SET
                risk_level = EXCLUDED.risk_level,
                comment = EXCLUDED.comment,
                gid_2 = EXCLUDED.gid_2,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            data.expert_type,
            data.assessment_date,
            data.country,
            data.admin1,
            data.admin2,
            data.gid_2,
            data.risk_level,
            data.comment,
        )

        return {
            "success": True,
            "id": row["id"],
            "message": "District risk level saved",
        }


@router.get("/districts/summary")
async def get_district_risk_summary(
    assessment_date: date = Query(..., description="Assessment date"),
    expert_type: Optional[Literal["hydrologist", "meteorologist"]] = Query(None),
):
    """
    Get summary of district risk levels by country.
    """
    async with get_connection() as conn:
        query = """
            SELECT
                country,
                risk_level,
                COUNT(*) as count
            FROM gha.district_risk_levels
            WHERE assessment_date = $1
        """
        params = [assessment_date]

        if expert_type:
            query += " AND expert_type = $2"
            params.append(expert_type)

        query += " GROUP BY country, risk_level ORDER BY country, risk_level"

        rows = await conn.fetch(query, *params)

        # Organize by country
        summary = {}
        for row in rows:
            country = row["country"]
            if country not in summary:
                summary[country] = {
                    "normal": 0,
                    "watch": 0,
                    "warning": 0,
                    "alarm": 0,
                    "emergency": 0,
                }
            summary[country][row["risk_level"]] = row["count"]

        return {
            "date": assessment_date.isoformat(),
            "expert_type": expert_type,
            "summary": summary,
        }


# =========================================================================
# Legacy-compatible endpoints matching CMS CountryAssessmentsView format
# Mounted under /api/v1/assessments/country-assessments/
# =========================================================================

@router.get("/country-assessments/")
async def legacy_country_assessments_get(
    date: Optional[str] = Query(None, alias="date"),
    expert_type: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    status: str = Query("all"),
    report_group: str = Query("all"),
    id: Optional[int] = Query(None),
    include_districts: str = Query("false"),
    include_snapshot: str = Query("false"),
    published: Optional[str] = Query(None),
):
    """Legacy-compatible GET /api/country-assessments/ matching CMS format."""
    from datetime import datetime as dt

    country_code = normalize_country_code(country) if country else ""
    include_dist = coerce_bool(include_districts, default=False)
    include_full_snapshot = coerce_bool(include_snapshot, default=False) or (id is not None)
    status = (status or "all").strip().lower()
    report_group = (report_group or "all").strip().lower()

    published_only = None
    if published is not None:
        published_only = coerce_bool(published, default=False)

    async with get_connection() as conn:
        query = """
            SELECT id, expert_type, assessment_date, valid_from, valid_to,
                   country_code, country_name, risk_level, assessment_comment,
                   affected_areas, recommendations, created_by, created_at,
                   updated_at, is_published
            FROM gha.expert_assessments
            WHERE 1=1
        """
        params = []
        idx = 1

        if id is not None:
            query += f" AND id = ${idx}"
            params.append(id)
            idx += 1

        if expert_type:
            query += f" AND expert_type = ${idx}"
            params.append(expert_type)
            idx += 1

        if date:
            query += f" AND assessment_date = ${idx}"
            params.append(dt.strptime(date, "%Y-%m-%d").date())
            idx += 1

        if country_code:
            if country_code == "REGION":
                query += " AND UPPER(COALESCE(country_code, 'REGION')) = 'REGION'"
            elif len(country_code) == 2:
                query += f" AND (UPPER(COALESCE(country_code, '')) = ${idx} OR LOWER(COALESCE(country_name, '')) = LOWER(${idx + 1}))"
                params.extend([country_code, country or country_code])
                idx += 2
            else:
                query += f" AND LOWER(COALESCE(country_name, '')) = LOWER(${idx})"
                params.append(country or country_code)
                idx += 1

        if status == "published":
            query += " AND COALESCE(is_published, FALSE) = TRUE"
        elif status in ("draft", "unapproved"):
            query += " AND COALESCE(is_published, FALSE) = FALSE"
        elif published_only is True:
            query += " AND COALESCE(is_published, FALSE) = TRUE"
        elif published_only is False:
            query += " AND COALESCE(is_published, FALSE) = FALSE"

        if report_group == "general":
            query += " AND UPPER(COALESCE(country_code, 'REGION')) = 'REGION'"
        elif report_group in ("member", "member_state", "member-state"):
            query += " AND UPPER(COALESCE(country_code, 'REGION')) != 'REGION'"

        query += " ORDER BY assessment_date DESC, country_name"

        rows = await conn.fetch(query, *params)

        assessments = []
        for row in rows:
            item = dict(row)
            assessment_date_raw = item.get("assessment_date")
            for df in ("assessment_date", "valid_from", "valid_to", "created_at", "updated_at"):
                if item.get(df) and hasattr(item[df], "isoformat"):
                    item[df] = item[df].isoformat()
                elif item.get(df):
                    item[df] = str(item[df])

            cc = normalize_country_code(item.get("country_code") or item.get("country_name")) or "REGION"
            item["country_code"] = cc
            if not item.get("country_name"):
                item["country_name"] = ISO2_TO_COUNTRY_NAME.get(cc, cc)

            item["report_group"] = "general" if cc == "REGION" else "member_state"
            item["status"] = "published" if item.get("is_published") else "draft"
            item["report_key"] = format_report_key(item.get("expert_type"), cc, item.get("assessment_date") or date or "")
            item.update(parse_creator_metadata(item.get("created_by")))
            item["district_count"] = 0
            if include_dist:
                item["district_assessments"] = []

            # Enrich with district data
            member_name = item.get("country_name") or ISO2_TO_COUNTRY_NAME.get(cc, cc)
            d_params = [item.get("expert_type"), assessment_date_raw]
            d_idx = 3

            if include_dist:
                d_query = """SELECT country, admin1, admin2, gid_2, risk_level, comment, created_at, updated_at
                             FROM gha.district_risk_levels WHERE expert_type = $1 AND assessment_date = $2"""
            else:
                d_query = "SELECT COUNT(*) FROM gha.district_risk_levels WHERE expert_type = $1 AND assessment_date = $2"

            if cc == "REGION":
                d_query += " AND UPPER(COALESCE(country, '')) LIKE 'REGION::%'"
            else:
                d_query += f" AND (UPPER(COALESCE(country, '')) = ${d_idx} OR LOWER(COALESCE(country, '')) = LOWER(${d_idx + 1}))"
                d_params.extend([cc, member_name])

            if include_dist:
                d_query += " ORDER BY country, admin1, admin2"
                d_rows = await conn.fetch(d_query, *d_params)
                districts = []
                for dr in d_rows:
                    dc = dr["country"]
                    if dc and dc.startswith("REGION::"):
                        dc = dc.split("REGION::", 1)[1]
                    districts.append({
                        "country": dc,
                        "admin1": dr["admin1"],
                        "admin2": dr["admin2"],
                        "gid_2": dr["gid_2"],
                        "risk_level": dr["risk_level"],
                        "comment": dr["comment"] or "",
                        "created_at": dr["created_at"].isoformat() if dr["created_at"] and hasattr(dr["created_at"], "isoformat") else str(dr["created_at"]) if dr["created_at"] else None,
                        "updated_at": dr["updated_at"].isoformat() if dr["updated_at"] and hasattr(dr["updated_at"], "isoformat") else str(dr["updated_at"]) if dr["updated_at"] else None,
                    })
                item["district_assessments"] = districts
                item["district_count"] = len(districts)
                item["interactive_report"] = {
                    "overall": {
                        "risk_level": item.get("risk_level", "normal"),
                        "assessment_comment": item.get("assessment_comment") or "",
                        "affected_areas": item.get("affected_areas") or "",
                        "recommendations": item.get("recommendations") or "",
                    },
                    "district_assessments": districts,
                }
            else:
                cnt_row = await conn.fetchrow(d_query, *d_params)
                item["district_count"] = int(cnt_row[0] or 0) if cnt_row else 0

            has_overall = bool(
                (item.get("assessment_comment") or "").strip()
                or (item.get("affected_areas") or "").strip()
                or (item.get("recommendations") or "").strip()
            )
            if item.get("is_published"):
                item["completion_state"] = "approved"
            elif has_overall or item.get("district_count", 0) > 0:
                item["completion_state"] = "unapproved"
            else:
                item["completion_state"] = "unfinished"

            assessments.append(item)

        if include_full_snapshot and assessments:
            assessment_ids = [int(item["id"]) for item in assessments if item.get("id")]
            snapshot_map = {}
            if assessment_ids:
                snapshot_rows = await conn.fetch(
                    """
                    SELECT assessment_id, snapshot_json, created_at, updated_at
                    FROM gha.report_snapshots
                    WHERE assessment_id = ANY($1::int[])
                    """,
                    assessment_ids,
                )
                for s_row in snapshot_rows:
                    snapshot_map[int(s_row["assessment_id"])] = {
                        "snapshot": s_row["snapshot_json"],
                        "created_at": s_row["created_at"],
                        "updated_at": s_row["updated_at"],
                    }

            for item in assessments:
                aid = int(item["id"]) if item.get("id") else None
                snapshot_data = snapshot_map.get(aid) if aid is not None else None
                if not snapshot_data:
                    item["full_report_snapshot"] = None
                    item["snapshot_created_at"] = None
                    item["snapshot_updated_at"] = None
                    continue

                item["full_report_snapshot"] = snapshot_data["snapshot"]
                created_at = snapshot_data["created_at"]
                updated_at = snapshot_data["updated_at"]
                item["snapshot_created_at"] = created_at.isoformat() if created_at and hasattr(created_at, "isoformat") else str(created_at) if created_at else None
                item["snapshot_updated_at"] = updated_at.isoformat() if updated_at and hasattr(updated_at, "isoformat") else str(updated_at) if updated_at else None

        return {"assessments": assessments, "count": len(assessments)}


@router.post("/country-assessments/")
async def legacy_country_assessments_post(request: Request):
    """Legacy-compatible POST /api/v1/assessments/country-assessments/ matching CMS format."""
    data = await request.json()

    valid_risk_levels = {"normal", "watch", "warning", "alarm", "emergency"}
    expert_type = (data.get("expert_type") or "hydrologist").strip().lower()
    if expert_type not in ("hydrologist", "meteorologist"):
        expert_type = "hydrologist"

    assessment_date_raw = data.get("forecast_date") or data.get("assessment_date")
    assessment_date = _parse_assessment_date_or_400(assessment_date_raw, field_name="assessment_date")
    report_group = (data.get("report_group") or "").strip().lower()
    raw_cc = data.get("country_code") or data.get("country")
    raw_cn = data.get("country_name")
    country_code = normalize_country_code(raw_cc or raw_cn)
    country_name = (raw_cn or "").strip()
    if not country_name and country_code:
        country_name = ISO2_TO_COUNTRY_NAME.get(country_code, country_code)

    if report_group == "general":
        country_code = "REGION"
        country_name = "East Africa Region"
    elif report_group in ("member", "member_state", "member-state") and (not country_code or country_code == "REGION"):
        raise HTTPException(status_code=400, detail="Member-state report requires a country")
    elif not country_code:
        country_code = "REGION"
        country_name = country_name or "East Africa Region"

    risk_level = (data.get("risk_level") or "normal").strip().lower()
    if risk_level not in valid_risk_levels:
        risk_level = "normal"

    comment = data.get("comment", "") or ""
    affected_areas = data.get("affected_areas", "") or ""
    recommendations = data.get("recommendations", "") or ""
    contributor_name = (data.get("contributor_name") or "").strip()
    contributor_country = normalize_country_code(data.get("contributor_country") or data.get("country_of_origin"))
    explicit_creator = (data.get("created_by") or "").strip()
    district_assessments = data.get("district_assessments")
    district_payload_provided = district_assessments is not None
    if district_payload_provided and not isinstance(district_assessments, list):
        raise HTTPException(status_code=400, detail="district_assessments must be a list")
    replace_district = coerce_bool(data.get("replace_district_assessments"), default=district_payload_provided)
    report_snapshot = data.get("report_snapshot")
    if report_snapshot is not None and not isinstance(report_snapshot, (dict, list)):
        raise HTTPException(status_code=400, detail="report_snapshot must be an object or array")

    save_mode = (data.get("save_mode") or "draft").strip().lower()
    is_published = coerce_bool(data.get("is_published"), default=save_mode in ("submitted", "publish", "published"))
    logged_in = coerce_bool(data.get("logged_in"), default=False)

    if country_code != "REGION" and not logged_in:
        raise HTTPException(status_code=403, detail="Sign-in is required for member-state expert assessments")

    if country_code == "REGION":
        display_name = contributor_name or explicit_creator or "public-user"
        display_country = contributor_country or "REGION"
        created_by = f"public|{display_name}|{display_country}"
    else:
        display_name = explicit_creator or contributor_name or "authenticated-user"
        created_by = f"kpp|{display_name}|{country_code}"

    if save_mode in ("submitted", "publish", "published") and not comment.strip():
        raise HTTPException(status_code=400, detail="Assessment comment is required")

    district_summary = {"normal": 0, "watch": 0, "warning": 0, "alarm": 0, "emergency": 0}
    for district in (district_assessments or []):
        if not isinstance(district, dict):
            continue
        d_risk = (district.get("risk_level") or "normal").strip().lower()
        if d_risk in district_summary:
            district_summary[d_risk] += 1

    if report_snapshot is None:
        report_snapshot = {
            "version": "1.0",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "context": {
                "report_group": report_group or ("general" if country_code == "REGION" else "member_state"),
                "expert_type": expert_type,
                "forecast_date": assessment_date.isoformat(),
                "country_code": country_code,
                "country_name": country_name,
                "save_mode": save_mode,
                "status": "published" if is_published else "draft",
            },
            "sections": {
                "interactive_report": {
                    "overall_risk_level": risk_level,
                    "overall_assessment_comment": comment,
                    "affected_areas": affected_areas,
                    "recommendations": recommendations,
                    "district_summary": district_summary,
                    "district_assessment_count": len(district_assessments or []),
                }
            },
        }

    district_saved_count = 0
    async with get_connection() as conn:
        async with conn.transaction():
            result = await conn.fetchrow("""
                INSERT INTO gha.expert_assessments
                    (expert_type, assessment_date, country_code, country_name,
                     risk_level, assessment_comment, affected_areas, recommendations,
                     created_by, is_published, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP)
                ON CONFLICT (expert_type, assessment_date, country_code)
                DO UPDATE SET
                    risk_level = EXCLUDED.risk_level,
                    assessment_comment = EXCLUDED.assessment_comment,
                    affected_areas = EXCLUDED.affected_areas,
                    recommendations = EXCLUDED.recommendations,
                    created_by = EXCLUDED.created_by,
                    country_name = EXCLUDED.country_name,
                    is_published = EXCLUDED.is_published,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, expert_type, assessment_date, country_code, country_name,
                risk_level, comment, affected_areas, recommendations, created_by, is_published)

            assessment_id = result["id"] if result else None

            if district_payload_provided:
                if replace_district:
                    if country_code == "REGION":
                        await conn.execute("""
                            DELETE FROM gha.district_risk_levels
                            WHERE expert_type = $1 AND assessment_date = $2
                              AND UPPER(COALESCE(country, '')) LIKE 'REGION::%'
                        """, expert_type, assessment_date)
                    else:
                        await conn.execute("""
                            DELETE FROM gha.district_risk_levels
                            WHERE expert_type = $1 AND assessment_date = $2
                              AND (UPPER(COALESCE(country, '')) = $3 OR LOWER(COALESCE(country, '')) = LOWER($4))
                        """, expert_type, assessment_date, country_code, country_name)

                for district in (district_assessments or []):
                    if not isinstance(district, dict):
                        continue
                    admin1 = (district.get("admin1") or district.get("name_1") or "").strip()
                    admin2 = (district.get("admin2") or district.get("name_2") or "").strip()
                    if not admin1 or not admin2:
                        continue

                    dcc = normalize_country_code(district.get("country_code") or district.get("country") or country_code)
                    if dcc == "REGION":
                        dcc = country_code if country_code != "REGION" else ""
                    dcn = (district.get("country_name") or "").strip()
                    if not dcn and dcc:
                        dcn = ISO2_TO_COUNTRY_NAME.get(dcc, "")
                    if not dcn and country_code != "REGION":
                        dcn = country_name
                    if not dcn:
                        dcn = (district.get("country") or "").strip()
                    if not dcn:
                        continue

                    d_risk = (district.get("risk_level") or "normal").strip().lower()
                    if d_risk not in valid_risk_levels:
                        d_risk = "normal"
                    d_comment = (district.get("comment") or "").strip()
                    d_gid_2 = (district.get("gid_2") or "").strip() or None
                    stored_country = f"REGION::{dcn}" if country_code == "REGION" else dcn

                    await conn.execute("""
                        INSERT INTO gha.district_risk_levels
                            (expert_type, assessment_date, country, admin1, admin2, gid_2, risk_level, comment, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
                        ON CONFLICT (expert_type, assessment_date, country, admin1, admin2)
                        DO UPDATE SET risk_level = EXCLUDED.risk_level, comment = EXCLUDED.comment,
                                      gid_2 = EXCLUDED.gid_2, updated_at = CURRENT_TIMESTAMP
                    """, expert_type, assessment_date, stored_country, admin1, admin2, d_gid_2, d_risk, d_comment)
                    district_saved_count += 1

            if assessment_id:
                await conn.execute(
                    """
                    INSERT INTO gha.report_snapshots (assessment_id, snapshot_json, updated_at)
                    VALUES ($1, $2::jsonb, CURRENT_TIMESTAMP)
                    ON CONFLICT (assessment_id)
                    DO UPDATE SET
                        snapshot_json = EXCLUDED.snapshot_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    assessment_id,
                    json.dumps(report_snapshot),
                )

    return {
        "success": True,
        "id": assessment_id,
        "status": "published" if is_published else "draft",
        "report_key": format_report_key(expert_type, country_code, assessment_date.isoformat()),
        "country_code": country_code,
        "country_name": country_name,
        "district_saved_count": district_saved_count,
        "replace_district_assessments": replace_district,
        "snapshot_saved": True,
        "full_saved": True,
        "message": "Expert assessment saved successfully",
    }


@router.post("/country-assessments/{assessment_id}/publish/")
async def legacy_country_assessment_publish(request: Request, assessment_id: int):
    """Legacy-compatible POST /api/v1/assessments/country-assessments/{id}/publish/"""
    try:
        data = await request.json() if await request.body() else {}
    except Exception:
        data = {}

    publish = coerce_bool(data.get("is_published"), default=True)

    async with get_connection() as conn:
        row = await conn.fetchrow("""
            UPDATE gha.expert_assessments
            SET is_published = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING id, is_published
        """, publish, assessment_id)

        if not row:
            raise HTTPException(status_code=404, detail="Assessment not found")

    return {
        "success": True,
        "id": row["id"],
        "is_published": row["is_published"],
        "status": "published" if row["is_published"] else "draft",
    }


@router.get("/risk-assessments/")
async def legacy_risk_assessments_get(
    date: Optional[str] = Query(None, alias="date"),
    expert_type: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
):
    """Legacy-compatible GET /api/v1/assessments/risk-assessments/"""
    async with get_connection() as conn:
        query = """
            SELECT id, expert_type, assessment_date, country, admin1, admin2,
                   gid_2, risk_level, comment, created_at, updated_at
            FROM gha.district_risk_levels WHERE 1=1
        """
        params = []
        idx = 1

        if date:
            parsed_date = _parse_assessment_date_or_400(date, field_name="date")
            query += f" AND assessment_date = ${idx}"
            params.append(parsed_date)
            idx += 1
        if expert_type:
            query += f" AND expert_type = ${idx}"
            params.append(expert_type)
            idx += 1
        if country:
            query += f" AND country = ${idx}"
            params.append(country)
            idx += 1

        query += " ORDER BY country, admin1, admin2"
        rows = await conn.fetch(query, *params)

        assessments = []
        for row in rows:
            item = dict(row)
            for df in ("assessment_date", "created_at", "updated_at"):
                if item.get(df) and hasattr(item[df], "isoformat"):
                    item[df] = item[df].isoformat()
                elif item.get(df):
                    item[df] = str(item[df])
            assessments.append(item)

        return {"assessments": assessments, "count": len(assessments)}


@router.post("/risk-assessments/")
async def legacy_risk_assessments_post(request: Request):
    """Legacy-compatible POST /api/v1/assessments/risk-assessments/"""
    data = await request.json()

    expert_type = data.get("expert_type", "hydrologist")
    assessment_date_raw = data.get("forecast_date") or data.get("assessment_date")
    assessment_date = _parse_assessment_date_or_400(assessment_date_raw, field_name="assessment_date")
    country = data.get("country")
    admin1 = data.get("admin1")
    admin2 = data.get("admin2")
    risk_level = data.get("risk_level", "normal")
    comment = data.get("comment", "")
    gid_2 = data.get("gid_2")

    if not all([country, admin1, admin2]):
        raise HTTPException(status_code=400, detail="Missing required fields: country, admin1, admin2")

    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO gha.district_risk_levels
                (expert_type, assessment_date, country, admin1, admin2, gid_2, risk_level, comment, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
            ON CONFLICT (expert_type, assessment_date, country, admin1, admin2)
            DO UPDATE SET risk_level = EXCLUDED.risk_level, comment = EXCLUDED.comment,
                          gid_2 = EXCLUDED.gid_2, updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, expert_type, assessment_date, country, admin1, admin2, gid_2, risk_level, comment)

        return {"success": True, "id": row["id"], "message": "District risk level saved"}
