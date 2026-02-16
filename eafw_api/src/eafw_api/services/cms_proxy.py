"""
Helpers for proxying compatibility endpoints to the Django CMS API.
"""
from __future__ import annotations

from typing import Any, Iterable

import httpx
from fastapi import HTTPException

from eafw_api.config import get_settings

settings = get_settings()

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=45.0, write=45.0, pool=45.0)


def _normalize_api_base(url: str) -> str:
    base = (url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/api"):
        return base
    return f"{base}/api"


def _candidate_api_bases() -> list[str]:
    configured = _normalize_api_base(settings.cms_api_base_url)
    candidates = [
        configured,
        "http://eafw_cms:8000/api",
        "http://127.0.0.1:9068/api",
        "http://localhost:9068/api",
    ]
    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _proxy_headers() -> dict[str, str]:
    headers = {"accept": "application/json"}
    host_header = (settings.cms_proxy_host_header or "").strip()
    if host_header:
        headers["host"] = host_header
    return headers


async def proxy_cms_json(
    path: str,
    query_items: Iterable[tuple[str, str]] | None = None,
) -> Any:
    """
    Fetch JSON from the upstream Django CMS API.

    Raises 502 if all upstream candidates fail or return invalid JSON.
    """
    endpoint_path = path if path.startswith("/") else f"/{path}"
    params = list(query_items or [])
    last_error = "unknown"

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        for api_base in _candidate_api_bases():
            upstream_url = f"{api_base}{endpoint_path}"

            try:
                response = await client.get(
                    upstream_url,
                    params=params,
                    headers=_proxy_headers(),
                )
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                continue

            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code} from {upstream_url}"
                continue

            try:
                return response.json()
            except ValueError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Upstream returned non-JSON response from {upstream_url}: {exc}",
                ) from exc

    raise HTTPException(
        status_code=502,
        detail=f"Failed to fetch upstream CMS endpoint {endpoint_path}. Last error: {last_error}",
    )
