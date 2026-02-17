"""
Storylines API - Serves published storylines with chapters for scrollytelling.
Reads from Wagtail StorylinePage via CMS database.

Author: Hillary Koros, ICPAC
"""
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from eafw_api.db import get_connection

router = APIRouter()


def _parse_streamfield(raw):
    """Parse StreamField JSON string or return as-is if already parsed."""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return raw


def _serialize_chapters(chapters_raw):
    """Convert StreamField chapters into clean JSON for the frontend."""
    chapters = _parse_streamfield(chapters_raw)
    result = []
    for item in chapters:
        if item.get("type") != "chapter":
            continue
        val = item.get("value", {})
        chapter = {
            "id": item.get("id", ""),
            "title": val.get("title", ""),
            "prose": val.get("prose", ""),
            "transition": val.get("transition", "fly"),
            "date_start": val.get("date_start"),
            "date_end": val.get("date_end"),
            "map_state": None,
            "media": [],
            "references": [],
        }
        # Map state
        ms = val.get("map_state")
        if ms:
            chapter["map_state"] = {
                "center": [ms.get("center_lon", 0), ms.get("center_lat", 0)],
                "zoom": ms.get("zoom", 5),
                "bearing": ms.get("bearing", 0),
                "pitch": ms.get("pitch", 0),
            }
        # Media
        media_raw = val.get("media", [])
        if isinstance(media_raw, list):
            for m in media_raw:
                media_item = {"type": m.get("type", ""), "value": m.get("value", {})}
                chapter["media"].append(media_item)
        # References
        refs = val.get("references", [])
        if isinstance(refs, list):
            chapter["references"] = [
                {"title": r.get("title", r.get("value", {}).get("title", "")),
                 "url": r.get("url", r.get("value", {}).get("url", ""))}
                for r in refs
            ]
        result.append(chapter)
    return result


def _serialize_country_events(events_raw):
    """Convert StreamField country events into clean JSON."""
    events = _parse_streamfield(events_raw)
    result = []
    for item in events:
        if item.get("type") != "event":
            continue
        val = item.get("value", {})
        result.append({
            "country": val.get("country", ""),
            "event_period": val.get("event_period", ""),
            "emdat_codes": val.get("emdat_codes", ""),
        })
    return result


@router.get("/")
async def list_storylines(
    region: Optional[str] = Query(None, description="Filter by region"),
):
    """List all published storylines (without full chapter content)."""
    async with get_connection() as conn:
        sql = """
            SELECT
                p.id,
                p.slug,
                p.title,
                s.description,
                s.event_start,
                s.event_end,
                s.region,
                s.total_affected,
                s.total_displaced,
                s.total_deaths,
                s.country_events,
                img.file AS cover_image
            FROM cms.storylines_storylinepage s
            JOIN cms.wagtailcore_page p ON s.page_ptr_id = p.id
            LEFT JOIN cms.wagtailimages_image img ON s.cover_image_id = img.id
            WHERE p.live = true
        """
        params = []
        if region:
            sql += " AND LOWER(s.region) = LOWER($1)"
            params.append(region)
        sql += " ORDER BY s.event_start DESC"

        rows = await conn.fetch(sql, *params)

    storylines = []
    for row in rows:
        storylines.append({
            "id": row["id"],
            "slug": row["slug"],
            "title": row["title"],
            "description": row["description"],
            "event_start": str(row["event_start"]) if row["event_start"] else None,
            "event_end": str(row["event_end"]) if row["event_end"] else None,
            "region": row["region"],
            "total_affected": row["total_affected"],
            "total_displaced": row["total_displaced"],
            "total_deaths": row["total_deaths"],
            "country_events": _serialize_country_events(row["country_events"]),
            "cover_image": f"/media/{row['cover_image']}" if row.get("cover_image") else None,
        })
    return {"storylines": storylines, "count": len(storylines)}


@router.get("/{slug}")
async def get_storyline(slug: str):
    """Get a single storyline with full chapter content for scrollytelling."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                p.id,
                p.slug,
                p.title,
                s.description,
                s.event_start,
                s.event_end,
                s.region,
                s.total_affected,
                s.total_displaced,
                s.total_deaths,
                s.country_events,
                s.chapters,
                img.file AS cover_image
            FROM cms.storylines_storylinepage s
            JOIN cms.wagtailcore_page p ON s.page_ptr_id = p.id
            LEFT JOIN cms.wagtailimages_image img ON s.cover_image_id = img.id
            WHERE p.slug = $1 AND p.live = true
            """,
            slug,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Storyline not found")

    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "description": row["description"],
        "event_start": str(row["event_start"]) if row["event_start"] else None,
        "event_end": str(row["event_end"]) if row["event_end"] else None,
        "region": row["region"],
        "total_affected": row["total_affected"],
        "total_displaced": row["total_displaced"],
        "total_deaths": row["total_deaths"],
        "country_events": _serialize_country_events(row["country_events"]),
        "chapters": _serialize_chapters(row["chapters"]),
        "cover_image": f"/media/{row['cover_image']}" if row.get("cover_image") else None,
    }
