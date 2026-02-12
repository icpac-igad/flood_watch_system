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

    # Mount v1 API router - all endpoints served under /api/v1/
    app.include_router(v1_router, prefix="/api/v1")

    return app


# Application instance
app = create_app()
