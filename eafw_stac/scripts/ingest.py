#!/usr/bin/env python3
"""
STAC Collection & Item Ingestion for FloodWatch.

Loads STAC collection definitions and items into pgSTAC via the STAC API.

Usage:
    python ingest.py load-collections --collections-dir /opt/collections
    python ingest.py load-items --items-dir /data/cogs
    python ingest.py load-all
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import click
import httpx

# Allow running as a standalone script inside /opt/scripts.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.settings import ScriptSettings
from lib.styles import preview_href, style_for_item

logger = logging.getLogger("stac_ingest")

SETTINGS = ScriptSettings()

STAC_API_URL = SETTINGS.stac_api_url
COLLECTIONS_DIR = SETTINGS.collections_dir
ITEMS_DIR = SETTINGS.items_dir
STATIC_ITEMS_DIR = SETTINGS.static_items_dir
MAX_RETRIES = 30
RETRY_DELAY = 5

PUBLIC_COG_PREFIX = SETTINGS.public_cog_prefix
PUBLIC_TITILER_PREFIX = SETTINGS.public_titiler_prefix


def _normalize_data_href(href: str, item_path: Path) -> str:
    """Normalize data href to publicly served /stac-cogs path when needed."""
    value = str(href).strip()
    if value.startswith(("http://", "https://", "/stac-cogs/", "/vsicurl/")):
        return value

    if value.startswith("/"):
        parts = value.split("/")
        if "cogs" in parts:
            rel = "/".join(parts[parts.index("cogs") + 1 :])
            return f"{PUBLIC_COG_PREFIX}/{rel}"
        return value

    if value.endswith((".tif", ".tiff")):
        parts = [p.lower() for p in item_path.parts]
        if "cogs" in parts:
            idx = parts.index("cogs")
            rel_parts = list(item_path.parts[idx + 1 : -1]) + [value]
            return f"{PUBLIC_COG_PREFIX}/{'/'.join(rel_parts)}"
        return f"{PUBLIC_COG_PREFIX}/{value}"

    return value


def _wait_for_stac_api(base_url: str, max_retries: int = MAX_RETRIES) -> bool:
    """Wait for the STAC API to be ready."""
    for i in range(max_retries):
        try:
            resp = httpx.get(f"{base_url}/", timeout=10)
            if resp.status_code == 200:
                logger.info("STAC API is ready at %s", base_url)
                return True
        except httpx.ConnectError:
            pass
        logger.info("Waiting for STAC API... (%d/%d)", i + 1, max_retries)
        time.sleep(RETRY_DELAY)
    logger.error("STAC API not available after %d attempts", max_retries)
    return False


def _load_collection(client: httpx.Client, collection_path: Path) -> bool:
    """Load a single STAC collection. Returns True on success."""
    with open(collection_path) as f:
        collection = json.load(f)

    coll_id = collection["id"]

    # Check if already exists
    resp = client.get(f"/collections/{coll_id}")
    if resp.status_code == 200:
        logger.info("Collection '%s' already exists, updating...", coll_id)
        resp = client.put(f"/collections/{coll_id}", json=collection)
    else:
        logger.info("Creating collection '%s'...", coll_id)
        resp = client.post("/collections", json=collection)

    if resp.status_code in (200, 201):
        logger.info("Collection '%s' loaded successfully", coll_id)
        return True

    logger.error(
        "Failed to load collection '%s': %d %s",
        coll_id, resp.status_code, resp.text[:200],
    )
    return False


def _load_item(client: httpx.Client, item_path: Path) -> bool:
    """Load a single STAC item. Returns True on success."""
    with open(item_path) as f:
        item = json.load(f)

    coll_id = item.get("collection")
    item_id = item.get("id")

    if not coll_id:
        coll_id = _infer_collection_id(item_path, item)
        if not coll_id:
            logger.warning("Item '%s' has no collection, skipping", item_path)
            return False
        item["collection"] = coll_id
        logger.info(
            "Inferred collection '%s' for item '%s' from path",
            coll_id,
            item_path.name,
        )

    # Normalize item assets for resilient discovery workflows.
    assets = item.setdefault("assets", {})
    data_asset = assets.get("data")
    if isinstance(data_asset, dict) and data_asset.get("href"):
        data_asset["href"] = _normalize_data_href(data_asset["href"], item_path)

    if item_id and data_asset:
        style = style_for_item(coll_id, item_id, item)
        preview = preview_href(
            coll_id,
            item_id,
            titiler_prefix=PUBLIC_TITILER_PREFIX,
            asset_key="data",
            style=style,
        )

        # For known raster collections, force styled thumbnail so UI is never gray.
        if style:
            assets["thumbnail"] = {
                "href": preview,
                "type": "image/png",
                "title": f"{item_id} thumbnail",
                "roles": ["thumbnail", "overview"],
            }
            links = item.setdefault("links", [])
            links = [l for l in links if l.get("rel") != "preview"]
            links.append(
                {
                    "rel": "preview",
                    "href": preview,
                    "type": "image/png",
                    "title": f"{item_id} preview",
                }
            )
            item["links"] = links

    # Check if already exists
    resp = client.get(f"/collections/{coll_id}/items/{item_id}")
    if resp.status_code == 200:
        logger.info("Item '%s' already exists, updating...", item_id)
        resp = client.put(f"/collections/{coll_id}/items/{item_id}", json=item)
    else:
        logger.info("Creating item '%s' in collection '%s'...", item_id, coll_id)
        resp = client.post(f"/collections/{coll_id}/items", json=item)

    if resp.status_code in (200, 201):
        logger.info("Item '%s' loaded successfully", item_id)
        return True

    logger.error(
        "Failed to load item '%s': %d %s",
        item_id, resp.status_code, resp.text[:200],
    )
    return False


def _infer_collection_id(item_path: Path, item: dict) -> Optional[str]:
    """Infer a STAC collection id from item path and id for discovery workflows."""
    text = f"{item_path} {item.get('id', '')}".lower()

    if "cmorph" in text or "virtualizarr" in text:
        return "cmorph-30min-virtualizarr-parquet"
    if "cropland" in text:
        return "asap-cropland"
    if "rangeland" in text:
        return "asap-rangeland"
    if "landscan" in text or "population" in text:
        return "landscan-population"
    if "return_period" in text or "25y" in text or "100y" in text or "m6_" in text:
        return "flood-extent-return-periods"
    if "multimodal" in text and ("whca" in text or "nile" in text):
        return "multimodal-points-whca"
    if "multimodal" in text:
        return "multimodal-points-gha"
    if "wrf-extreme-rainfall" in text:
        return "wrf-extreme-rainfall"
    if "wrf" in text or "rainfall" in text:
        return "wrf-daily-rainfall"
    return None


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _collect_item_files(items_dir: Path) -> list[Path]:
    """Collect item files with dynamic-discovery items taking precedence.

    Any static template item from ``STATIC_ITEMS_DIR`` is skipped when the same
    collection already has discovered COG sidecar items under ``items_dir``.
    This avoids duplicate items for raster collections while keeping static-only
    collections (e.g., metadata/vector catalogs).
    """

    dynamic_files = sorted(items_dir.rglob("*.json")) if items_dir.exists() else []
    static_files = (
        sorted(STATIC_ITEMS_DIR.rglob("*.json"))
        if STATIC_ITEMS_DIR.exists() and STATIC_ITEMS_DIR != items_dir
        else []
    )

    def _read_item(path: Path) -> dict:
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    dynamic_collections = set()
    dynamic_keys = set()
    for file_path in dynamic_files:
        item = _read_item(file_path)
        coll_id = item.get("collection") or _infer_collection_id(file_path, item)
        item_id = item.get("id")
        if coll_id:
            dynamic_collections.add(coll_id)
        if coll_id and item_id:
            dynamic_keys.add((coll_id, item_id))

    selected = list(dynamic_files)
    for file_path in static_files:
        item = _read_item(file_path)
        coll_id = item.get("collection") or _infer_collection_id(file_path, item)
        item_id = item.get("id")

        if coll_id in dynamic_collections:
            logger.info(
                "Skipping static item '%s' for collection '%s' (discovered items present)",
                file_path.name,
                coll_id,
            )
            continue

        if coll_id and item_id and (coll_id, item_id) in dynamic_keys:
            logger.info(
                "Skipping duplicate static item '%s' (%s/%s)",
                file_path.name,
                coll_id,
                item_id,
            )
            continue

        selected.append(file_path)

    # deterministic path uniqueness
    seen_paths = set()
    unique_files = []
    for file_path in selected:
        key = str(file_path.resolve())
        if key in seen_paths:
            continue
        seen_paths.add(key)
        unique_files.append(file_path)
    return unique_files


@click.group()
@click.option("-v", "--verbose", is_flag=True)
def cli(verbose: bool):
    """FloodWatch STAC ingestion utility."""
    _setup_logging(verbose)


@cli.command("load-collections")
@click.option("--collections-dir", type=click.Path(exists=True, path_type=Path), default=str(COLLECTIONS_DIR))
@click.option("--api-url", type=str, default=STAC_API_URL)
def load_collections(collections_dir: Path, api_url: str):
    """Load all STAC collection JSON files."""
    if not _wait_for_stac_api(api_url):
        sys.exit(1)

    client = httpx.Client(base_url=api_url, timeout=30)
    files = sorted(collections_dir.glob("*.json"))
    if not files:
        click.echo(f"No collection files found in {collections_dir}")
        return

    ok = sum(1 for f in files if _load_collection(client, f))
    click.echo(f"Loaded {ok}/{len(files)} collections")
    if ok < len(files):
        sys.exit(1)


@cli.command("load-items")
@click.option("--items-dir", type=click.Path(exists=True, path_type=Path), default=str(ITEMS_DIR))
@click.option("--api-url", type=str, default=STAC_API_URL)
def load_items(items_dir: Path, api_url: str):
    """Load all STAC item JSON files from the COG directory."""
    if not _wait_for_stac_api(api_url):
        sys.exit(1)

    client = httpx.Client(base_url=api_url, timeout=30)
    files = _collect_item_files(items_dir)
    if not files:
        click.echo(f"No item files found in {items_dir} or {STATIC_ITEMS_DIR}")
        return

    ok = sum(1 for f in files if _load_item(client, f))
    click.echo(f"Loaded {ok}/{len(files)} items")


@cli.command("load-all")
@click.option("--collections-dir", type=click.Path(path_type=Path), default=str(COLLECTIONS_DIR))
@click.option("--items-dir", type=click.Path(path_type=Path), default=str(ITEMS_DIR))
@click.option("--api-url", type=str, default=STAC_API_URL)
def load_all(collections_dir: Path, items_dir: Path, api_url: str):
    """Load all collections then all items."""
    if not _wait_for_stac_api(api_url):
        sys.exit(1)

    client = httpx.Client(base_url=api_url, timeout=30)

    # Collections first
    coll_files = sorted(collections_dir.glob("*.json")) if collections_dir.exists() else []
    if coll_files:
        ok = sum(1 for f in coll_files if _load_collection(client, f))
        click.echo(f"Collections: {ok}/{len(coll_files)} loaded")

    # Then items
    item_files = _collect_item_files(items_dir)
    if item_files:
        ok = sum(1 for f in item_files if _load_item(client, f))
        click.echo(f"Items: {ok}/{len(item_files)} loaded")

    if not coll_files and not item_files:
        click.echo("No collections or items found to load")


if __name__ == "__main__":
    cli()
