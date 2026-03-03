"""
CAP (Common Alerting Protocol) Alerts Router
Proxies to Django CMS cap-composer endpoints.

Author: Hillary Koros
Organization: ICPAC
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from eafw_api.config import get_settings

router = APIRouter()
settings = get_settings()

CMS_BASE = settings.cms_base_url.rstrip("/") if hasattr(settings, "cms_base_url") else "http://eafw_cms:8000"


class CapDraftRequest(BaseModel):
    assessment_id: int
    expires_hours: int = 48


class CapForecastDraftRequest(BaseModel):
    country_code: str | None = None  # ISO-2 code, omit for all countries
    expires_hours: int = 48


class CapDraftResponse(BaseModel):
    success: bool
    cap_alert_id: int | None = None
    edit_url: str | None = None
    message: str


@router.post("/draft", response_model=CapDraftResponse)
async def create_cap_draft(request: CapDraftRequest):
    """Create a draft CAP alert from a published expert assessment."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{CMS_BASE}/cms-api/cap/create-draft/",
                json=request.model_dump(),
                timeout=30.0,
            )
            data = resp.json()
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=data.get("message", "Error"))
            return data
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"CMS unreachable: {str(e)}")


@router.post("/forecast-draft")
async def create_cap_forecast_draft(request: CapForecastDraftRequest):
    """
    Create CAP alert drafts from live multimodal forecast data.

    Queries current forecast points, groups by country, and creates
    a CAP draft for each country with points at warning level or above.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{CMS_BASE}/cms-api/cap/create-forecast-draft/",
                json=request.model_dump(),
                timeout=60.0,
            )
            data = resp.json()
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=data.get("message", "Error"))
            return data
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"CMS unreachable: {str(e)}")


@router.get("/alerts")
async def get_cap_alerts():
    """Get active CAP alerts as GeoJSON (proxied from cap-composer)."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{CMS_BASE}/api/cap/alerts.geojson",
                timeout=10.0,
            )
            return resp.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"CMS unreachable: {str(e)}")


@router.get("/rss")
async def get_cap_rss():
    """Get CAP alerts RSS feed (proxied from cap-composer)."""
    from fastapi.responses import Response
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{CMS_BASE}/api/cap/rss.xml",
                timeout=10.0,
            )
            return Response(content=resp.content, media_type="application/rss+xml")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"CMS unreachable: {str(e)}")
