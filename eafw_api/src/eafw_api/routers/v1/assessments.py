"""
Expert Assessments API - FloodWatch specific
For hydrologists and meteorologists risk assessments
"""
from typing import Optional, Literal
from datetime import date
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from eafw_api.db import get_connection

router = APIRouter()


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
