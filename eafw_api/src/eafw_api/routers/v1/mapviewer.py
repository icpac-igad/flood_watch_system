"""
Mapviewer compatibility endpoints.
"""
from fastapi import APIRouter, Request

from eafw_api.services.cms_proxy import proxy_cms_json

router = APIRouter()


@router.get("/mapviewer-config")
@router.get("/mapviewer-config/")
async def get_mapviewer_config(request: Request):
    """
    Return mapviewer config payload compatible with legacy Django endpoint.
    """
    return await proxy_cms_json(
        path="/mapviewer-config",
        query_items=request.query_params.multi_items(),
        source_request=request,
    )
