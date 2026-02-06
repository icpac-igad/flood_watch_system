"""
FloodWatch API - Main Application
Fast, async API service for East Africa Flood Watch

Author: Hillary Koros
Organization: ICPAC
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from eafw_api.config import get_settings
from eafw_api.db import create_pool, close_pool
from eafw_api.routers.v1 import router as v1_router
from eafw_api.routers.v1.multimodal import router as multimodal_router
from eafw_api.middleware import RateLimitMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    await create_pool()
    yield
    # Shutdown
    await close_pool()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Rate limiting middleware (external users only)
    app.add_middleware(RateLimitMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": "eafw-api", "version": settings.app_version}

    # Mount v1 API router
    app.include_router(v1_router, prefix="/api/v1")

    # Legacy routes for backward compatibility with homepage widgets
    # These routes are at /api/ instead of /api/v1/
    app.include_router(
        multimodal_router,
        prefix="/api/multimodal",
        tags=["Legacy - Multimodal"],
        include_in_schema=False  # Hide from docs since they're aliases
    )

    # Redirect legacy endpoint names to new ones
    from eafw_api.routers.v1.multimodal import (
        get_country_summary_with_bounds,
        get_situation_summary,
    )
    from eafw_api.routers.v1.boundaries import get_admin_boundaries_legacy
    from eafw_api.routers.v1.basins import get_basin_geometry

    app.get("/api/country-summary-with-bounds/", tags=["Legacy"], include_in_schema=False)(
        get_country_summary_with_bounds
    )
    app.get("/api/situation-summary/", tags=["Legacy"], include_in_schema=False)(
        get_situation_summary
    )

    # Legacy admin-boundaries endpoint (flat JSON array format)
    app.get("/api/admin-boundaries/", tags=["Legacy"], include_in_schema=False)(
        get_admin_boundaries_legacy
    )
    app.get("/api/admin-boundaries", tags=["Legacy"], include_in_schema=False)(
        get_admin_boundaries_legacy
    )

    # Legacy basin geometry endpoint (for BasinLayer)
    app.get("/api/basin/{hybas_id}/", tags=["Legacy"], include_in_schema=False)(
        get_basin_geometry
    )
    app.get("/api/basin/{hybas_id}", tags=["Legacy"], include_in_schema=False)(
        get_basin_geometry
    )

    return app


# Application instance
app = create_app()
