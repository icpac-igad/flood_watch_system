from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode


WRF_DAILY_STYLE: dict[str, Any] = {
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
}


WRF_EXTREME_STYLE: dict[str, Any] = {
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
}


STYLE_PRESETS: dict[str, dict[str, Any]] = {
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
        **WRF_DAILY_STYLE,
    },
    "wrf-extreme-rainfall": {
        **WRF_EXTREME_STYLE,
    },
    "wrf-extreme-rainfall-f90": {
        **WRF_EXTREME_STYLE,
    },
    "wrf-extreme-rainfall-f95": {
        **WRF_EXTREME_STYLE,
    },
    "wrf-extreme-rainfall-f99": {
        **WRF_EXTREME_STYLE,
    },
}


def style_for_item(collection_id: str, item_id: str, item: dict[str, Any]) -> dict[str, Any]:
    if collection_id.startswith("wrf-extreme-rainfall"):
        return WRF_EXTREME_STYLE
    return STYLE_PRESETS.get(collection_id, {})


def preview_href(
    collection_id: str,
    item_id: str,
    titiler_prefix: str,
    asset_key: str = "data",
    style: dict[str, Any] | None = None,
) -> str:
    params = {"assets": asset_key}
    style = style or STYLE_PRESETS.get(collection_id, {})
    if "colormap" in style:
        params["colormap"] = json.dumps(style["colormap"], separators=(",", ":"))
    if "resampling" in style:
        params["resampling"] = style["resampling"]
    if "rescale" in style:
        params["rescale"] = style["rescale"]
    return (
        f"{titiler_prefix}/collections/{collection_id}/items/{item_id}/preview.png?"
        f"{urlencode(params)}"
    )

