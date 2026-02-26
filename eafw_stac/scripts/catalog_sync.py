#!/usr/bin/env python3
"""
Modular STAC catalog sync and cleanup utility.

This script keeps the runtime STAC API aligned with FloodWatch canonical items:
- removes legacy duplicate item IDs
- optionally prunes deprecated collections
- upserts static metadata items (e.g., CMORPH parquet catalog item)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Iterable

import click
import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.settings import (
    DEFAULT_PRUNE_COLLECTIONS,
    LEGACY_ITEMS,
    ScriptSettings,
)

LOGGER = logging.getLogger("catalog_sync")

SETTINGS = ScriptSettings()
DEFAULT_API_URL = SETTINGS.stac_api_url
DEFAULT_CMORPH_ITEM = SETTINGS.cmorph_item_file


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _safe_get(client: httpx.Client, path: str) -> httpx.Response:
    try:
        return client.get(path)
    except Exception as exc:
        raise click.ClickException(f"GET failed for {path}: {exc}") from exc


def _safe_delete(client: httpx.Client, path: str) -> httpx.Response:
    try:
        return client.delete(path)
    except Exception as exc:
        raise click.ClickException(f"DELETE failed for {path}: {exc}") from exc


def _safe_post(client: httpx.Client, path: str, payload: dict) -> httpx.Response:
    try:
        return client.post(path, json=payload)
    except Exception as exc:
        raise click.ClickException(f"POST failed for {path}: {exc}") from exc


def _safe_put(client: httpx.Client, path: str, payload: dict) -> httpx.Response:
    try:
        return client.put(path, json=payload)
    except Exception as exc:
        raise click.ClickException(f"PUT failed for {path}: {exc}") from exc


def _item_exists(client: httpx.Client, collection_id: str, item_id: str) -> bool:
    resp = _safe_get(client, f"/collections/{collection_id}/items/{item_id}")
    return resp.status_code == 200


def _collection_exists(client: httpx.Client, collection_id: str) -> bool:
    resp = _safe_get(client, f"/collections/{collection_id}")
    return resp.status_code == 200


def _load_item(item_path: Path) -> dict:
    if not item_path.exists():
        raise click.ClickException(f"Item file does not exist: {item_path}")
    with item_path.open() as fp:
        return json.load(fp)


def _upsert_item(client: httpx.Client, item: dict) -> None:
    collection_id = item.get("collection")
    item_id = item.get("id")
    if not collection_id or not item_id:
        raise click.ClickException("Item must contain both 'collection' and 'id'")

    if _item_exists(client, collection_id, item_id):
        resp = _safe_put(client, f"/collections/{collection_id}/items/{item_id}", item)
        if resp.status_code not in (200, 201):
            raise click.ClickException(
                f"Failed to update item {collection_id}/{item_id}: "
                f"{resp.status_code} {resp.text[:200]}"
            )
        LOGGER.info("Updated item: %s/%s", collection_id, item_id)
        return

    resp = _safe_post(client, f"/collections/{collection_id}/items", item)
    if resp.status_code not in (200, 201):
        raise click.ClickException(
            f"Failed to create item {collection_id}/{item_id}: "
            f"{resp.status_code} {resp.text[:200]}"
        )
    LOGGER.info("Created item: %s/%s", collection_id, item_id)


def _delete_item_if_exists(client: httpx.Client, collection_id: str, item_id: str) -> bool:
    if not _item_exists(client, collection_id, item_id):
        return False
    resp = _safe_delete(client, f"/collections/{collection_id}/items/{item_id}")
    if resp.status_code not in (200, 202, 204):
        raise click.ClickException(
            f"Failed to delete item {collection_id}/{item_id}: "
            f"{resp.status_code} {resp.text[:200]}"
        )
    LOGGER.info("Deleted legacy item: %s/%s", collection_id, item_id)
    return True


def _delete_collection_if_exists(client: httpx.Client, collection_id: str) -> bool:
    if not _collection_exists(client, collection_id):
        return False
    resp = _safe_delete(client, f"/collections/{collection_id}")
    if resp.status_code not in (200, 202, 204):
        raise click.ClickException(
            f"Failed to delete collection {collection_id}: "
            f"{resp.status_code} {resp.text[:200]}"
        )
    LOGGER.info("Deleted collection: %s", collection_id)
    return True


def _next_path(base_url: httpx.URL, links: list[dict]) -> str | None:
    for link in links or []:
        if link.get("rel") != "next":
            continue
        href = link.get("href")
        if not href:
            continue
        if href.startswith(("http://", "https://")):
            try:
                parsed = httpx.URL(href)
                query = parsed.query.decode() if parsed.query else ""
                return f"{parsed.path}?{query}" if query else parsed.path
            except Exception:
                # Fallback: strip known base URL if present.
                href_str = str(href)
                base_str = str(base_url).rstrip("/")
                return href_str.replace(base_str, "", 1) if href_str.startswith(base_str) else href_str
        return href
    return None


def _count_collection_items(client: httpx.Client, collection_id: str, limit: int = 200) -> int | None:
    path = f"/collections/{collection_id}/items?limit={limit}"
    total = 0
    visited = set()

    while path and path not in visited:
        visited.add(path)
        resp = _safe_get(client, path)
        if resp.status_code != 200:
            return None
        payload = resp.json()
        total += len(payload.get("features", []))
        path = _next_path(client.base_url, payload.get("links", []))
    return total


def _iter_collection_items(client: httpx.Client, collection_id: str, limit: int = 200):
    """Yield all items in a collection, following pagination links."""
    path = f"/collections/{collection_id}/items?limit={limit}"
    visited = set()

    while path and path not in visited:
        visited.add(path)
        resp = _safe_get(client, path)
        if resp.status_code != 200:
            raise click.ClickException(
                f"Failed to list items for {collection_id}: {resp.status_code} {resp.text[:200]}"
            )
        payload = resp.json()
        for feature in payload.get("features", []):
            yield feature
        path = _next_path(client.base_url, payload.get("links", []))


def _cleanup_wrf_misrouted_items(client: httpx.Client) -> int:
    """Delete extreme-rainfall items accidentally inserted in daily collection."""
    collection_id = "wrf-daily-rainfall"
    deleted = 0

    for item in list(_iter_collection_items(client, collection_id)):
        item_id = item.get("id", "")
        props = item.get("properties") or {}

        is_misrouted_extreme = item_id.startswith("wrf-extreme-") or ("wrf:percentile" in props)
        if not is_misrouted_extreme:
            continue

        if _delete_item_if_exists(client, collection_id, item_id):
            deleted += 1

    return deleted


@click.group()
@click.option("--api-url", default=DEFAULT_API_URL, show_default=True, help="STAC API base URL.")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, api_url: str, verbose: bool) -> None:
    """STAC catalog sync utilities."""
    _setup_logging(verbose)
    ctx.obj = {"api_url": api_url}


@cli.command("audit")
@click.pass_context
def audit(ctx: click.Context) -> None:
    """Print collection and item counts."""
    api_url = ctx.obj["api_url"]
    with httpx.Client(base_url=api_url, timeout=30) as client:
        resp = _safe_get(client, "/collections")
        if resp.status_code != 200:
            raise click.ClickException(f"Failed to list collections: {resp.status_code} {resp.text[:200]}")
        payload = resp.json()
        collections = payload.get("collections", [])
        click.echo(f"Collections: {len(collections)}")
        for coll in collections:
            cid = coll.get("id")
            if not cid:
                continue
            count = _count_collection_items(client, cid)
            if count is None:
                click.echo(f"  - {cid}: items=unknown")
                continue
            click.echo(f"  - {cid}: items={count}")


@cli.command("cleanup-legacy-items")
@click.pass_context
def cleanup_legacy_items(ctx: click.Context) -> None:
    """Delete known legacy duplicate item IDs."""
    api_url = ctx.obj["api_url"]
    deleted = 0
    with httpx.Client(base_url=api_url, timeout=30) as client:
        for collection_id, item_ids in LEGACY_ITEMS.items():
            for item_id in item_ids:
                if _delete_item_if_exists(client, collection_id, item_id):
                    deleted += 1

        deleted += _cleanup_wrf_misrouted_items(client)
    click.echo(f"Deleted legacy items: {deleted}")


@cli.command("prune-collections")
@click.option(
    "--collection-id",
    "collection_ids",
    multiple=True,
    help="Collection ID to prune. If omitted, uses default deprecated list.",
)
@click.pass_context
def prune_collections(ctx: click.Context, collection_ids: Iterable[str]) -> None:
    """Delete deprecated collections if they exist."""
    targets = list(collection_ids) if collection_ids else list(DEFAULT_PRUNE_COLLECTIONS)
    api_url = ctx.obj["api_url"]
    deleted = 0
    with httpx.Client(base_url=api_url, timeout=30) as client:
        for collection_id in targets:
            if _delete_collection_if_exists(client, collection_id):
                deleted += 1
    click.echo(f"Deleted collections: {deleted}")


@cli.command("upsert-item")
@click.option(
    "--item-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Path to a STAC item JSON file.",
)
@click.pass_context
def upsert_item(ctx: click.Context, item_file: Path) -> None:
    """Upsert a static STAC item JSON document."""
    api_url = ctx.obj["api_url"]
    item = _load_item(item_file)
    with httpx.Client(base_url=api_url, timeout=30) as client:
        _upsert_item(client, item)
    click.echo(f"Upserted item: {item.get('collection')}/{item.get('id')}")


@cli.command("sync-defaults")
@click.option(
    "--cmorph-item-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=DEFAULT_CMORPH_ITEM,
    show_default=True,
    help="Path to CMORPH static item JSON.",
)
@click.pass_context
def sync_defaults(ctx: click.Context, cmorph_item_file: Path) -> None:
    """Run standard cleanup + upserts for FloodWatch."""
    api_url = ctx.obj["api_url"]
    with httpx.Client(base_url=api_url, timeout=30) as client:
        # 1) Remove duplicate legacy items.
        for collection_id, item_ids in LEGACY_ITEMS.items():
            for item_id in item_ids:
                _delete_item_if_exists(client, collection_id, item_id)

        # 1b) Remove known WRF misroutes (extreme items under daily collection).
        _cleanup_wrf_misrouted_items(client)

        # 2) Remove deprecated collections if present.
        for collection_id in DEFAULT_PRUNE_COLLECTIONS:
            _delete_collection_if_exists(client, collection_id)

        # 3) Upsert static CMORPH reference item.
        cmorph_item = _load_item(cmorph_item_file)
        _upsert_item(client, cmorph_item)

    click.echo("Catalog defaults synchronized.")


if __name__ == "__main__":
    cli()
