"""
Datasets API - Replaces DRF DatasetViewSet
Provides layer/dataset information from CMS
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from datetime import datetime

from eafw_api.db import get_connection
from eafw_api.services.cms_proxy import proxy_cms_json

router = APIRouter()


class DatasetResponse(BaseModel):
    id: str
    title: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    summary: Optional[str] = None
    published: bool = True
    layer_type: Optional[str] = None
    metadata_id: Optional[int] = None
    latest_date: Optional[datetime] = None


class DatasetListResponse(BaseModel):
    datasets: list[DatasetResponse]
    count: int


@router.get("/mapviewer")
@router.get("/mapviewer/")
async def list_mapviewer_datasets(request: Request):
    """
    Mapviewer-compatible dataset payload (legacy /api/datasets/ shape).
    """
    return await proxy_cms_json(
        path="/datasets/",
        query_items=request.query_params.multi_items(),
        source_request=request,
    )


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    category: Optional[str] = Query(None, description="Filter by category"),
    published: bool = Query(True, description="Filter by published status"),
):
    """
    List all published datasets with layers.
    Equivalent to DRF DatasetViewSet.list()
    """
    async with get_connection() as conn:
        query = """
            SELECT
                d.id::text,
                d.title,
                c.title as category,
                sc.title as sub_category,
                d.summary,
                d.published,
                d.latest_date
            FROM cms.geomanager_dataset d
            LEFT JOIN cms.geomanager_category c ON d.category_id = c.id
            LEFT JOIN cms.geomanager_subcategory sc ON d.sub_category_id = sc.id
            WHERE d.published = $1
        """
        params = [published]

        if category:
            query += " AND c.title = $2"
            params.append(category)

        query += " ORDER BY c.title, d.title"

        rows = await conn.fetch(query, *params)

        datasets = [
            DatasetResponse(
                id=str(row["id"]),
                title=row["title"],
                category=row["category"],
                sub_category=row["sub_category"],
                summary=row["summary"],
                published=row["published"],
                latest_date=row["latest_date"],
            )
            for row in rows
        ]

        return DatasetListResponse(datasets=datasets, count=len(datasets))


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    """
    Get dataset by ID.
    Equivalent to DRF DatasetViewSet.retrieve()
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                d.id::text,
                d.title,
                c.title as category,
                sc.title as sub_category,
                d.summary,
                d.published,
                d.latest_date,
                m.id as metadata_id
            FROM cms.geomanager_dataset d
            LEFT JOIN cms.geomanager_category c ON d.category_id = c.id
            LEFT JOIN cms.geomanager_subcategory sc ON d.sub_category_id = sc.id
            LEFT JOIN cms.geomanager_metadata m ON d.id = m.dataset_id
            WHERE d.id::text = $1
            """,
            dataset_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return DatasetResponse(
            id=str(row["id"]),
            title=row["title"],
            category=row["category"],
            sub_category=row["sub_category"],
            summary=row["summary"],
            published=row["published"],
            latest_date=row["latest_date"],
            metadata_id=row["metadata_id"],
        )


@router.get("/slug/{slug}")
async def get_dataset_by_slug(slug: str):
    """
    Get dataset by slug.
    Equivalent to DRF DatasetSlugViewSet.retrieve()
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                d.id::text,
                d.title,
                d.dataset_slug,
                c.title as category,
                sc.title as sub_category,
                d.summary,
                d.published,
                d.latest_date
            FROM cms.geomanager_dataset d
            LEFT JOIN cms.geomanager_category c ON d.category_id = c.id
            LEFT JOIN cms.geomanager_subcategory sc ON d.sub_category_id = sc.id
            WHERE d.dataset_slug = $1
            """,
            slug,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return {
            "id": str(row["id"]),
            "title": row["title"],
            "slug": row["dataset_slug"],
            "category": row["category"],
            "sub_category": row["sub_category"],
            "summary": row["summary"],
            "published": row["published"],
            "latest_date": row["latest_date"].isoformat() if row["latest_date"] else None,
        }
