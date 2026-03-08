"""
Security utilities for the FloodWatch STAC integration.

Handles API key validation, input sanitization, and parameter validation.
Write operations (POST/PUT/DELETE) are protected by API key via nginx.
"""
import hmac
import re
from datetime import datetime
from typing import Optional, Tuple

# GHoA bounding box limits (with buffer)
GHOA_BBOX_MIN_LON = 15.0
GHOA_BBOX_MIN_LAT = -18.0
GHOA_BBOX_MAX_LON = 58.0
GHOA_BBOX_MAX_LAT = 28.0

# Valid ID pattern: alphanumeric, hyphens, underscores, dots
_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,255}$")


def validate_api_key(provided_key: str, expected_key: str) -> bool:
    """Constant-time API key comparison to prevent timing attacks."""
    if not expected_key:
        return False
    return hmac.compare_digest(provided_key.encode(), expected_key.encode())


def sanitize_id(value: str) -> str:
    """Sanitize a STAC collection or item ID.

    Returns the sanitized value or raises ValueError.
    """
    value = value.strip()
    if not _ID_PATTERN.match(value):
        raise ValueError(
            f"Invalid ID '{value}': must be alphanumeric with hyphens/underscores/dots, "
            f"1-256 characters, starting with alphanumeric"
        )
    return value


def validate_bbox(bbox: list) -> Tuple[bool, Optional[str]]:
    """Validate a STAC search bbox parameter.

    Args:
        bbox: [west, south, east, north] in EPSG:4326

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False, "bbox must be [west, south, east, north]"

    try:
        west, south, east, north = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return False, "bbox values must be numeric"

    if not (-180 <= west <= 180 and -180 <= east <= 180):
        return False, "longitude must be between -180 and 180"
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        return False, "latitude must be between -90 and 90"
    if south >= north:
        return False, "south must be less than north"
    if west >= east:
        return False, "west must be less than east"

    # Warn if bbox is outside GHoA region (but don't reject)
    if (west > GHOA_BBOX_MAX_LON or east < GHOA_BBOX_MIN_LON or
            south > GHOA_BBOX_MAX_LAT or north < GHOA_BBOX_MIN_LAT):
        return True, "warning: bbox is outside the Greater Horn of Africa region"

    return True, None


def validate_datetime(dt_string: str) -> Tuple[bool, Optional[str]]:
    """Validate a STAC datetime or datetime interval string.

    Supports: single datetime, open intervals (..), and closed intervals (/).
    """
    if not dt_string:
        return False, "datetime string is empty"

    parts = dt_string.split("/")
    if len(parts) > 2:
        return False, "datetime interval must have at most two parts separated by /"

    for part in parts:
        if part == "..":
            continue
        try:
            datetime.fromisoformat(part.replace("Z", "+00:00"))
        except ValueError:
            return False, f"invalid datetime format: '{part}'"

    if len(parts) == 2 and parts[0] == ".." and parts[1] == "..":
        return False, "both sides of interval cannot be open"

    return True, None


def generate_nginx_rate_limit_config(
    requests_per_minute: int = 100,
    burst: int = 20,
    zone_name: str = "stac_search",
    zone_size: str = "10m",
) -> str:
    """Generate nginx rate limiting configuration snippet."""
    return (
        f"limit_req_zone $binary_remote_addr zone={zone_name}:{zone_size} "
        f"rate={requests_per_minute}r/m;\n"
        f"# Usage in location block:\n"
        f"# limit_req zone={zone_name} burst={burst} nodelay;\n"
    )
