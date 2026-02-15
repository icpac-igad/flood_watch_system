"""
WRF Rainfall API - Available dates for WRF daily and extreme rainfall layers.
"""
from fastapi import APIRouter
from eafw_api.db import get_connection

router = APIRouter()


@router.get("/daily-rainfall/dates")
async def daily_rainfall_dates():
    """Return available dates for WRF daily rainfall."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT valid_date FROM wrf.daily_rainfall ORDER BY valid_date"
        )
    return {"timestamps": [r["valid_date"].isoformat() for r in rows]}


@router.get("/extreme-rainfall/dates")
async def extreme_rainfall_dates():
    """Return available dates for WRF extreme rainfall."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT forecast_date FROM wrf.extreme_rainfall ORDER BY forecast_date"
        )
    return {"timestamps": [r["forecast_date"].isoformat() for r in rows]}
