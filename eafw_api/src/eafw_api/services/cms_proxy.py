"""
Helpers for proxying compatibility endpoints to the Django CMS API.
"""
from __future__ import annotations

from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import HTTPException, Request

from eafw_api.config import get_settings

settings = get_settings()

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=45.0, write=45.0, pool=45.0)
URL_PREFIXES_TO_ABSOLUTIZE = (
    "/api/",
    "/pg/",
    "/mapserver/",
    "/mapcache/",
    "/cog-tiles/",
    "/stac/",
    "/stac-browser/",
    "/stac-assets/",
    "/stac-cogs/",
    "/stac-rasters/",
    "/media/",
    "/static/",
    "/mapviewer/",
)


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


def _proxy_headers(source_request: Request | None = None) -> dict[str, str]:
    headers = {"accept": "application/json"}
    request_host = ""
    if source_request:
        request_host = (source_request.headers.get("host") or "").strip()

    host_header = request_host or (settings.cms_proxy_host_header or "").strip()
    if host_header:
        headers["host"] = host_header
        headers["x-forwarded-host"] = host_header

    if source_request:
        forwarded_proto = (
            source_request.headers.get("x-forwarded-proto")
            or source_request.url.scheme
            or ""
        ).strip()
        if forwarded_proto:
            headers["x-forwarded-proto"] = forwarded_proto

        forwarded_port = (source_request.headers.get("x-forwarded-port") or "").strip()
        if forwarded_port:
            headers["x-forwarded-port"] = forwarded_port

        forwarded_for = (source_request.headers.get("x-forwarded-for") or "").strip()
        if forwarded_for:
            headers["x-forwarded-for"] = forwarded_for

    return headers


def _request_base_url(source_request: Request | None = None) -> str:
    if not source_request:
        return ""

    host = (
        source_request.headers.get("x-forwarded-host")
        or source_request.headers.get("host")
        or source_request.url.netloc
        or ""
    ).split(",")[0].strip()
    if not host:
        return ""

    scheme = (
        source_request.headers.get("x-forwarded-proto")
        or source_request.url.scheme
        or "http"
    ).split(",")[0].strip()

    return f"{scheme}://{host}"


def _normalize_string_url(value: str, request_base_url: str) -> str:
    if not value or not request_base_url:
        return value

    if value.startswith(("http://", "https://")):
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").lower()
        if hostname in {"127.0.0.1", "localhost", "0.0.0.0", "::1"}:
            replacement = urlsplit(request_base_url)
            return urlunsplit(
                (
                    replacement.scheme,
                    replacement.netloc,
                    parsed.path,
                    parsed.query,
                    parsed.fragment,
                )
            )
        return value

    if value.startswith(URL_PREFIXES_TO_ABSOLUTIZE):
        return f"{request_base_url.rstrip('/')}{value}"

    return value


def _normalize_payload_urls(payload: Any, request_base_url: str) -> Any:
    if isinstance(payload, dict):
        return {
            key: _normalize_payload_urls(value, request_base_url)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_normalize_payload_urls(item, request_base_url) for item in payload]
    if isinstance(payload, str):
        return _normalize_string_url(payload, request_base_url)
    return payload


async def proxy_cms_json(
    path: str,
    query_items: Iterable[tuple[str, str]] | None = None,
    source_request: Request | None = None,
) -> Any:
    """
    Fetch JSON from the upstream Django CMS API.

    Raises 502 if all upstream candidates fail or return invalid JSON.
    """
    endpoint_path = path if path.startswith("/") else f"/{path}"
    params = list(query_items or [])
    last_error = "unknown"

    request_base_url = _request_base_url(source_request)

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        for api_base in _candidate_api_bases():
            upstream_url = f"{api_base}{endpoint_path}"

            try:
                response = await client.get(
                    upstream_url,
                    params=params,
                    headers=_proxy_headers(source_request),
                )
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                continue

            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code} from {upstream_url}"
                continue

            try:
                payload = response.json()
                return _normalize_payload_urls(payload, request_base_url)
            except ValueError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Upstream returned non-JSON response from {upstream_url}: {exc}",
                ) from exc

    raise HTTPException(
        status_code=502,
        detail=f"Failed to fetch upstream CMS endpoint {endpoint_path}. Last error: {last_error}",
    )
