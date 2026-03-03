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


def _parse_listblock(raw):
    """Normalize ListBlock payloads, handling both bare values and {'value': ...} wrappers."""
    if not isinstance(raw, list):
        return []
    parsed = []
    for item in raw:
        if isinstance(item, dict) and "value" in item:
            parsed.append(item["value"])
        else:
            parsed.append(item)
    return parsed


def _safe_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_media_url(value):
    """Convert a stored file path to a URL served via /media."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        if v.startswith(("http://", "https://", "/")):
            return v
        return f"/media/{v}"
    return None


def _extract_media_asset_ids(chapters_raw):
    """Collect image/document IDs referenced by chapter media for batched lookup."""
    chapters = _parse_streamfield(chapters_raw)
    image_ids = set()
    document_ids = set()

    for item in chapters:
        if item.get("type") != "chapter":
            continue
        val = item.get("value", {})
        media_raw = val.get("media", [])
        if not isinstance(media_raw, list):
            continue

        for media_item in media_raw:
            if not isinstance(media_item, dict):
                continue

            media_type = media_item.get("type")
            media_value = media_item.get("value")

            if media_type == "image":
                image_id = None
                if isinstance(media_value, dict):
                    image_id = _safe_int(
                        media_value.get("id")
                        or media_value.get("image")
                        or media_value.get("pk")
                    )
                else:
                    image_id = _safe_int(media_value)
                if image_id is not None:
                    image_ids.add(image_id)

            elif media_type == "uploaded_video":
                doc_id = None
                if isinstance(media_value, dict):
                    doc_id = _safe_int(
                        media_value.get("file")
                        or media_value.get("document")
                        or media_value.get("id")
                    )
                else:
                    doc_id = _safe_int(media_value)
                if doc_id is not None:
                    document_ids.add(doc_id)

    return image_ids, document_ids


async def _resolve_media_assets(conn, image_ids, document_ids):
    """Resolve image/document IDs to file paths."""
    image_files = {}
    document_files = {}

    if image_ids:
        image_rows = await conn.fetch(
            """
            SELECT id, file
            FROM cms.wagtailimages_image
            WHERE id = ANY($1::int[])
            """,
            list(image_ids),
        )
        image_files = {row["id"]: str(row["file"]) for row in image_rows if row.get("file")}

    if document_ids:
        document_rows = await conn.fetch(
            """
            SELECT id, file
            FROM cms.wagtaildocs_document
            WHERE id = ANY($1::int[])
            """,
            list(document_ids),
        )
        document_files = {
            row["id"]: str(row["file"])
            for row in document_rows
            if row.get("file")
        }

    return image_files, document_files


def _normalize_media_item(media_item, image_files, document_files):
    """Normalize media items and resolve image/document IDs to URLs."""
    media_type = media_item.get("type", "")
    media_value = media_item.get("value")

    if media_type == "image":
        normalized = {}
        image_id = None

        if isinstance(media_value, dict):
            image_id = _safe_int(
                media_value.get("id") or media_value.get("image") or media_value.get("pk")
            )
            normalized.update(media_value)
        else:
            image_id = _safe_int(media_value)

        if image_id is not None:
            normalized["id"] = image_id
            resolved = _to_media_url(image_files.get(image_id))
            if resolved:
                normalized["url"] = resolved
        elif isinstance(media_value, str):
            resolved = _to_media_url(media_value)
            if resolved:
                normalized["url"] = resolved

        return {"type": media_type, "value": normalized if normalized else media_value}

    if media_type == "external_image":
        if isinstance(media_value, dict):
            return {"type": media_type, "value": media_value}
        return {"type": media_type, "value": {}}

    if media_type == "embed":
        if isinstance(media_value, dict):
            return {"type": media_type, "value": media_value}
        return {"type": media_type, "value": {"url": media_value} if media_value else {}}

    if media_type == "external_video":
        if isinstance(media_value, dict):
            normalized = dict(media_value)
        elif isinstance(media_value, str):
            normalized = {"url": media_value}
        else:
            normalized = {}
        if "muted" not in normalized:
            normalized["muted"] = True
        return {"type": media_type, "value": normalized}

    if media_type == "uploaded_video":
        if isinstance(media_value, dict):
            normalized = dict(media_value)
            doc_id = _safe_int(
                media_value.get("file")
                or media_value.get("document")
                or media_value.get("id")
            )
            if doc_id is not None:
                normalized["document_id"] = doc_id
                resolved = _to_media_url(document_files.get(doc_id))
                if resolved:
                    normalized["url"] = resolved
        elif media_value is not None:
            doc_id = _safe_int(media_value)
            normalized = {"document_id": doc_id}
            resolved = _to_media_url(document_files.get(doc_id))
            if resolved:
                normalized["url"] = resolved
        else:
            normalized = {}
        if "muted" not in normalized:
            normalized["muted"] = True
        return {"type": media_type, "value": normalized}

    return {"type": media_type, "value": media_value}


def _serialize_chapters(chapters_raw, image_files=None, document_files=None):
    """Convert StreamField chapters into clean JSON for the frontend."""
    chapters = _parse_streamfield(chapters_raw)
    image_files = image_files or {}
    document_files = document_files or {}

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
            "map_overlays": [],
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

        # Chapter map overlays (GeoJSON)
        map_overlays = _parse_listblock(val.get("map_overlays", []))
        for overlay in map_overlays:
            if not isinstance(overlay, dict):
                continue
            url = overlay.get("url")
            if not url:
                continue
            chapter["map_overlays"].append(
                {
                    "label": overlay.get("label"),
                    "url": url,
                    "layer_type": overlay.get("layer_type", "fill"),
                    "color": overlay.get("color", "#38bdf8"),
                    "opacity": max(0, min(1, _safe_float(overlay.get("opacity"), 0.45))),
                    "line_width": max(0, _safe_float(overlay.get("line_width"), 2)),
                    "point_radius": max(0, _safe_float(overlay.get("point_radius"), 5)),
                }
            )

        # Media
        media_raw = val.get("media", [])
        if isinstance(media_raw, list):
            for m in media_raw:
                if not isinstance(m, dict):
                    continue
                chapter["media"].append(
                    _normalize_media_item(m, image_files=image_files, document_files=document_files)
                )

        # References
        refs = val.get("references", [])
        refs_values = _parse_listblock(refs)
        chapter["references"] = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
            }
            for r in refs_values
            if isinstance(r, dict) and r.get("url")
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
        result.append(
            {
                "country": val.get("country", ""),
                "event_period": val.get("event_period", ""),
                "emdat_codes": val.get("emdat_codes", ""),
            }
        )
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
        storylines.append(
            {
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
                "cover_image": (
                    f"/media/{row['cover_image']}" if row.get("cover_image") else None
                ),
            }
        )
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

        image_ids, document_ids = _extract_media_asset_ids(row["chapters"])
        image_files, document_files = await _resolve_media_assets(
            conn,
            image_ids=image_ids,
            document_ids=document_ids,
        )

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
        "chapters": _serialize_chapters(
            row["chapters"],
            image_files=image_files,
            document_files=document_files,
        ),
        "cover_image": f"/media/{row['cover_image']}" if row.get("cover_image") else None,
    }
