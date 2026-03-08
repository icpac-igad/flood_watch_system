"""
Health check module for FloodWatch STAC services.

Checks pgSTAC database, STAC API, and titiler connectivity.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import httpx


async def check_pgstac_health(dsn: str | None = None) -> Dict[str, Any]:
    """Check pgSTAC database connectivity."""
    if dsn is None:
        host = os.getenv("PGSTAC_HOST", "eafw_pgdb")
        port = os.getenv("PGSTAC_PORT", "5432")
        db = os.getenv("PGSTAC_DB", "pgstac")
        user = os.getenv("PGSTAC_USER", "pgstac")
        password = os.getenv("PGSTAC_PASSWORD", "")
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            result = await conn.execute("SELECT version()")
            row = await result.fetchone()
            return {
                "service": "pgstac",
                "status": "healthy",
                "version": row[0] if row else "unknown",
            }
    except Exception as e:
        return {"service": "pgstac", "status": "unhealthy", "error": str(e)}


async def check_stac_api_health(base_url: str | None = None) -> Dict[str, Any]:
    """Check STAC API responsiveness."""
    if base_url is None:
        base_url = os.getenv("STAC_API_URL", "http://eafw_stac:8080")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "service": "stac-api",
                    "status": "healthy",
                    "title": data.get("title", "unknown"),
                    "stac_version": data.get("stac_version", "unknown"),
                }
            return {
                "service": "stac-api",
                "status": "unhealthy",
                "http_status": resp.status_code,
            }
    except Exception as e:
        return {"service": "stac-api", "status": "unhealthy", "error": str(e)}


async def check_titiler_health(base_url: str | None = None) -> Dict[str, Any]:
    """Check titiler-pgstac responsiveness."""
    if base_url is None:
        base_url = os.getenv("TITILER_URL", "http://eafw_titiler:80")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/healthz")
            if resp.status_code == 200:
                return {"service": "titiler", "status": "healthy"}
            return {
                "service": "titiler",
                "status": "unhealthy",
                "http_status": resp.status_code,
            }
    except Exception as e:
        return {"service": "titiler", "status": "unhealthy", "error": str(e)}


async def check_all_services(
    pgstac_dsn: str | None = None,
    stac_api_url: str | None = None,
    titiler_url: str | None = None,
) -> Dict[str, Any]:
    """Run all health checks concurrently and return combined status."""
    results = await asyncio.gather(
        check_pgstac_health(pgstac_dsn),
        check_stac_api_health(stac_api_url),
        check_titiler_health(titiler_url),
        return_exceptions=True,
    )

    services = []
    for r in results:
        if isinstance(r, Exception):
            services.append({"service": "unknown", "status": "error", "error": str(r)})
        else:
            services.append(r)

    all_healthy = all(s.get("status") == "healthy" for s in services)

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
    }
