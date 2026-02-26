"""Shared COG utilities for FloodWatch raster pipelines.

Constants and helpers used by cog_convert.py and wrf_cog_export.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

# ---------------------------------------------------------------------------
# Public URL prefixes (overridable via env for non-standard deployments)
# ---------------------------------------------------------------------------
PUBLIC_COG_PREFIX = os.getenv("STAC_COG_PUBLIC_PREFIX", "/stac-cogs")
PUBLIC_TITILER_PREFIX = os.getenv("TITILER_PUBLIC_PREFIX", "/cog-tiles")

# Greater Horn of Africa bounding box (west, south, east, north)
GHA_BBOX = (21.0, -12.0, 52.0, 23.0)

# ---------------------------------------------------------------------------
# TiTiler style presets — colormaps, resampling, and rescale per collection
# ---------------------------------------------------------------------------
STYLE_PRESETS = {
    "flood-extent-return-periods": {
        "colormap": {
            0: [0, 0, 0, 0],
            1: [222, 235, 247, 255],
            2: [198, 219, 239, 255],
            3: [158, 202, 225, 255],
            4: [107, 174, 214, 255],
            5: [49, 130, 189, 255],
            6: [8, 81, 156, 255],
        },
        "resampling": "nearest",
    },
    "asap-cropland": {
        "colormap": {
            0: [0, 0, 0, 0],
            1: [207, 198, 201, 255],
            20: [207, 198, 201, 255],
            21: [255, 255, 203, 255],
            40: [255, 255, 203, 255],
            41: [204, 225, 172, 255],
            80: [204, 225, 172, 255],
            81: [152, 195, 141, 255],
            120: [152, 195, 141, 255],
            121: [100, 164, 110, 255],
            160: [100, 164, 110, 255],
            161: [48, 134, 80, 255],
            255: [48, 134, 80, 255],
        },
        "resampling": "nearest",
    },
    "asap-rangeland": {
        "colormap": {
            0: [0, 0, 0, 0],
            1: [207, 198, 201, 255],
            20: [207, 198, 201, 255],
            21: [255, 255, 203, 255],
            40: [255, 255, 203, 255],
            41: [204, 225, 172, 255],
            80: [204, 225, 172, 255],
            81: [152, 195, 141, 255],
            120: [152, 195, 141, 255],
            121: [100, 164, 110, 255],
            160: [100, 164, 110, 255],
            161: [48, 134, 80, 255],
            255: [48, 134, 80, 255],
        },
        "resampling": "nearest",
    },
    "landscan-population": {
        "colormap": {
            0: [0, 0, 0, 0],
            1: [255, 255, 190, 255],
            5: [255, 255, 190, 255],
            6: [255, 255, 115, 255],
            25: [255, 255, 115, 255],
            26: [255, 255, 0, 255],
            50: [255, 255, 0, 255],
            51: [255, 170, 0, 255],
            100: [255, 170, 0, 255],
            101: [255, 102, 0, 255],
            500: [255, 102, 0, 255],
            501: [255, 0, 0, 255],
            2500: [255, 0, 0, 255],
            2501: [204, 0, 0, 255],
            5000: [204, 0, 0, 255],
            5001: [115, 0, 0, 255],
            65535: [115, 0, 0, 255],
        },
        "resampling": "bilinear",
    },
    "wrf-daily-rainfall": {
        "colormap": {
            0: [0, 0, 0, 0],
            1: [217, 217, 217, 255],
            2: [255, 176, 0, 255],
            10: [255, 176, 0, 255],
            11: [255, 242, 51, 255],
            30: [255, 242, 51, 255],
            31: [157, 255, 88, 255],
            50: [157, 255, 88, 255],
            51: [50, 230, 70, 255],
            100: [50, 230, 70, 255],
            101: [27, 157, 55, 255],
            200: [27, 157, 55, 255],
            201: [27, 157, 55, 255],
            2000: [27, 157, 55, 255],
        },
        "resampling": "bilinear",
        "rescale": "0,200",
    },
    "wrf-extreme-rainfall": {
        "colormap": {
            0: [0, 0, 0, 0],
            19: [0, 0, 0, 0],
            20: [152, 223, 238, 255],
            50: [152, 223, 238, 255],
            51: [43, 123, 216, 255],
            100: [43, 123, 216, 255],
            101: [9, 26, 136, 255],
            2000: [9, 26, 136, 255],
        },
        "resampling": "bilinear",
        "rescale": "0,300",
    },
}


def public_cog_href(cog_path: Path) -> str:
    """Convert local COG path to the publicly served STAC href."""
    parts = list(cog_path.as_posix().split("/"))
    if "cogs" in parts:
        rel = "/".join(parts[parts.index("cogs") + 1:])
        return f"{PUBLIC_COG_PREFIX}/{rel}"
    return str(cog_path)


def build_titiler_preview_href(
    collection_id: str,
    item_id: str,
    style_override: Optional[dict] = None,
    asset_key: str = "data",
) -> str:
    """Build a TiTiler preview URL for a STAC item.

    Uses STYLE_PRESETS[collection_id] by default; pass *style_override*
    to use a custom style dict instead.
    """
    style = style_override or STYLE_PRESETS.get(collection_id, {})
    params = {"assets": asset_key}

    colormap = style.get("colormap")
    if colormap:
        params["colormap"] = json.dumps(colormap, separators=(",", ":"))

    resampling = style.get("resampling")
    if resampling:
        params["resampling"] = resampling

    rescale = style.get("rescale")
    if rescale:
        params["rescale"] = rescale

    return (
        f"{PUBLIC_TITILER_PREFIX}/collections/{collection_id}"
        f"/items/{item_id}/preview.png?{urlencode(params)}"
    )
