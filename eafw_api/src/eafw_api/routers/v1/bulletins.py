"""
Flood Bulletins API - Published expert assessment reports
"""
from typing import Optional, Literal
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from eafw_api.db import get_connection

router = APIRouter()


class BulletinCreate(BaseModel):
    bulletin_number: Optional[str] = Field(None, max_length=50)
    title: str = Field(..., max_length=300)
    assessment_date: date
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    overall_risk_level: Literal["normal", "watch", "warning", "alarm", "emergency"] = "normal"
    executive_summary: Optional[str] = None
    hydrologist_assessment_id: Optional[int] = None
    meteorologist_assessment_id: Optional[int] = None
    additional_notes: Optional[str] = None
    created_by: Optional[str] = None


@router.get("/")
async def list_bulletins(
    published_only: bool = Query(True, description="Only return published bulletins"),
    risk_level: Optional[Literal["normal", "watch", "warning", "alarm", "emergency"]] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List flood bulletins.
    """
    async with get_connection() as conn:
        query = """
            SELECT
                b.id, b.bulletin_number, b.title, b.assessment_date,
                b.valid_from, b.valid_to, b.overall_risk_level,
                b.executive_summary, b.is_published, b.published_at,
                b.created_by, b.created_at, b.updated_at,
                ha.risk_level as hydro_risk, ha.assessment_comment as hydro_comment,
                ma.risk_level as meteo_risk, ma.assessment_comment as meteo_comment
            FROM gha.flood_bulletins b
            LEFT JOIN gha.expert_assessments ha ON b.hydrologist_assessment_id = ha.id
            LEFT JOIN gha.expert_assessments ma ON b.meteorologist_assessment_id = ma.id
            WHERE 1=1
        """
        params = []
        param_idx = 1

        if published_only:
            query += " AND b.is_published = TRUE"

        if risk_level:
            query += f" AND b.overall_risk_level = ${param_idx}"
            params.append(risk_level)
            param_idx += 1

        query += f" ORDER BY b.assessment_date DESC, b.id DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

        bulletins = []
        for row in rows:
            bulletin = {
                "id": row["id"],
                "bulletin_number": row["bulletin_number"],
                "title": row["title"],
                "assessment_date": row["assessment_date"].isoformat() if row["assessment_date"] else None,
                "valid_from": row["valid_from"].isoformat() if row["valid_from"] else None,
                "valid_to": row["valid_to"].isoformat() if row["valid_to"] else None,
                "overall_risk_level": row["overall_risk_level"],
                "executive_summary": row["executive_summary"],
                "is_published": row["is_published"],
                "published_at": row["published_at"].isoformat() if row["published_at"] else None,
                "hydrologist_assessment": {
                    "risk_level": row["hydro_risk"],
                    "comment": row["hydro_comment"],
                } if row["hydro_risk"] else None,
                "meteorologist_assessment": {
                    "risk_level": row["meteo_risk"],
                    "comment": row["meteo_comment"],
                } if row["meteo_risk"] else None,
            }
            bulletins.append(bulletin)

        return {
            "bulletins": bulletins,
            "count": len(bulletins),
            "limit": limit,
            "offset": offset,
        }


@router.post("/", status_code=201)
async def create_bulletin(data: BulletinCreate):
    """
    Create a new flood bulletin.
    """
    async with get_connection() as conn:
        # Auto-generate bulletin number if not provided
        bulletin_number = data.bulletin_number
        if not bulletin_number:
            year = data.assessment_date.year
            count = await conn.fetchval(
                """
                SELECT COUNT(*) + 1
                FROM gha.flood_bulletins
                WHERE EXTRACT(YEAR FROM assessment_date) = $1
                """,
                year,
            )
            bulletin_number = f"FB-{year}-{count:03d}"

        row = await conn.fetchrow(
            """
            INSERT INTO gha.flood_bulletins
                (bulletin_number, title, assessment_date, valid_from, valid_to,
                 overall_risk_level, executive_summary, hydrologist_assessment_id,
                 meteorologist_assessment_id, additional_notes, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id, bulletin_number
            """,
            bulletin_number,
            data.title,
            data.assessment_date,
            data.valid_from,
            data.valid_to,
            data.overall_risk_level,
            data.executive_summary,
            data.hydrologist_assessment_id,
            data.meteorologist_assessment_id,
            data.additional_notes,
            data.created_by,
        )

        return {
            "success": True,
            "id": row["id"],
            "bulletin_number": row["bulletin_number"],
            "message": "Flood bulletin created",
        }


@router.get("/{bulletin_id}")
async def get_bulletin(bulletin_id: int):
    """
    Get a specific flood bulletin with full details.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                b.id, b.bulletin_number, b.title, b.assessment_date,
                b.valid_from, b.valid_to, b.overall_risk_level,
                b.executive_summary, b.additional_notes,
                b.is_published, b.published_at,
                b.created_by, b.created_at, b.updated_at,
                b.hydrologist_assessment_id, b.meteorologist_assessment_id
            FROM gha.flood_bulletins b
            WHERE b.id = $1
            """,
            bulletin_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Bulletin not found")

        # Get linked assessments
        hydro_assessment = None
        meteo_assessment = None

        if row["hydrologist_assessment_id"]:
            hydro = await conn.fetchrow(
                "SELECT * FROM gha.expert_assessments WHERE id = $1",
                row["hydrologist_assessment_id"],
            )
            if hydro:
                hydro_assessment = dict(hydro)

        if row["meteorologist_assessment_id"]:
            meteo = await conn.fetchrow(
                "SELECT * FROM gha.expert_assessments WHERE id = $1",
                row["meteorologist_assessment_id"],
            )
            if meteo:
                meteo_assessment = dict(meteo)

        return {
            "id": row["id"],
            "bulletin_number": row["bulletin_number"],
            "title": row["title"],
            "assessment_date": row["assessment_date"].isoformat() if row["assessment_date"] else None,
            "valid_from": row["valid_from"].isoformat() if row["valid_from"] else None,
            "valid_to": row["valid_to"].isoformat() if row["valid_to"] else None,
            "overall_risk_level": row["overall_risk_level"],
            "executive_summary": row["executive_summary"],
            "additional_notes": row["additional_notes"],
            "is_published": row["is_published"],
            "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            "hydrologist_assessment": hydro_assessment,
            "meteorologist_assessment": meteo_assessment,
            "created_by": row["created_by"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }


@router.patch("/{bulletin_id}/publish")
async def publish_bulletin(bulletin_id: int):
    """
    Publish a flood bulletin.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            UPDATE gha.flood_bulletins
            SET is_published = TRUE, published_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id, bulletin_number
            """,
            bulletin_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Bulletin not found")

        return {
            "success": True,
            "bulletin_number": row["bulletin_number"],
            "message": "Bulletin published successfully",
        }


@router.get("/latest/summary")
async def get_latest_bulletin_summary():
    """
    Get the latest published bulletin summary.
    Useful for homepage display.
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                b.id, b.bulletin_number, b.title, b.assessment_date,
                b.valid_from, b.valid_to, b.overall_risk_level,
                b.executive_summary, b.published_at
            FROM gha.flood_bulletins b
            WHERE b.is_published = TRUE
            ORDER BY b.published_at DESC
            LIMIT 1
            """
        )

        if not row:
            return {"bulletin": None, "message": "No published bulletins"}

        return {
            "bulletin": {
                "id": row["id"],
                "bulletin_number": row["bulletin_number"],
                "title": row["title"],
                "assessment_date": row["assessment_date"].isoformat(),
                "valid_from": row["valid_from"].isoformat() if row["valid_from"] else None,
                "valid_to": row["valid_to"].isoformat() if row["valid_to"] else None,
                "overall_risk_level": row["overall_risk_level"],
                "executive_summary": row["executive_summary"],
                "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            }
        }
