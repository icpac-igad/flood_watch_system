from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScriptSettings:
    stac_api_url: str = os.getenv("STAC_API_URL", "http://localhost:9070")
    collections_dir: Path = Path(os.getenv("COLLECTIONS_DIR", "/opt/collections"))
    items_dir: Path = Path(os.getenv("COG_DATA_DIR", "/data/cogs"))
    static_items_dir: Path = Path(os.getenv("STATIC_ITEMS_DIR", "/opt/items"))
    public_cog_prefix: str = os.getenv("STAC_COG_PUBLIC_PREFIX", "/stac-cogs")
    public_titiler_prefix: str = os.getenv("TITILER_PUBLIC_PREFIX", "/cog-tiles")
    cmorph_item_file: Path = Path(
        os.getenv(
            "CMORPH_ITEM_FILE",
            "eafw_stac/items/cmorph_30min_virtualizarr_catalog_item.json",
        )
    )


LEGACY_ITEMS: dict[str, list[str]] = {
    "asap-cropland": ["asap-cropland-1km-2026"],
    "asap-rangeland": ["asap-rangeland-1km-2026"],
    "flood-extent-return-periods": [
        "flood-extent-25y-2026",
        "flood-extent-100y-2026",
    ],
    "wrf-daily-rainfall": ["wrf-daily-rainfall-2026-02-17"],
}


DEFAULT_PRUNE_COLLECTIONS = (
    "flood-impact",
    "indicator-points",
    "nile-basin-points",
)
