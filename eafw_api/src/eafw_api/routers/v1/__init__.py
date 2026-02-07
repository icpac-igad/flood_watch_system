"""
FloodWatch API v1 Router
Combines all v1 endpoints

Author: Hillary Koros
Organization: ICPAC
"""
from fastapi import APIRouter

from .datasets import router as datasets_router
from .boundaries import router as boundaries_router
from .assessments import router as assessments_router
from .forecasts import router as forecasts_router
from .bulletins import router as bulletins_router
from .cms import router as cms_router
from .multimodal import router as multimodal_router
from .basins import router as basins_router

router = APIRouter(tags=["v1"])

# Include sub-routers
router.include_router(cms_router, prefix="/cms", tags=["CMS Content"])
router.include_router(datasets_router, prefix="/datasets", tags=["Datasets"])
router.include_router(boundaries_router, prefix="/boundaries", tags=["Boundaries"])
router.include_router(assessments_router, prefix="/assessments", tags=["Expert Assessments"])
router.include_router(forecasts_router, prefix="/forecasts", tags=["Forecasts"])
router.include_router(bulletins_router, prefix="/bulletins", tags=["Flood Bulletins"])
router.include_router(multimodal_router, prefix="/multimodal", tags=["Multimodal Forecasts"])
router.include_router(basins_router, prefix="/basins", tags=["HydroBasins"])
