"""Manual publish pipeline for JRC masked flood hazard rasters.

This script is designed for deployments that do not run a scheduler.
It takes the output manifest from ``jrc_flood_hazard_mask.py`` and performs:

1) per-return-period mosaicking of masked tiles,
2) COG generation,
3) STAC item upsert to the configured STAC API,
4) CMS raster tile URL updates so mapviewer uses the new STAC items.

Usage example:

    python -m pyfloodwatch.jrc_stac_publish \
      --manifest gpr/jrc_flood_hazard_masked/manifest.csv \
      --return-periods 25,100 \
      --item-date 2026-03-04
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

import psycopg2
import rasterio
import requests
from rasterio.transform import array_bounds
from rasterio.warp import transform_bounds

LOGGER = logging.getLogger("jrc_stac_publish")

DEFAULT_COLLECTION_ID = "flood-extent-return-periods"
DEFAULT_DATASET_SLUG = "flood-extent-hazard"
DEFAULT_STAC_API_URL = os.getenv("STAC_API_URL", "http://eafw_stac:8080")
DEFAULT_STAC_COG_PREFIX = os.getenv("STAC_COG_PUBLIC_PREFIX", "/stac-cogs")
DEFAULT_TITILER_PREFIX = os.getenv("TITILER_PUBLIC_PREFIX", "/cog-tiles")
DEFAULT_COLLECTION_JSON_CANDIDATES = (
    "eafw_stac/collections/flood_extent_return_periods.json",
    "/opt/collections/flood_extent_return_periods.json",
)

# Flood extent color ramp kept aligned with existing STAC/TiTiler presets.
FLOOD_COLORMAP = {
    0: [0, 0, 0, 0],
    1: [222, 235, 247, 255],
    2: [198, 219, 239, 255],
    3: [158, 202, 225, 255],
    4: [107, 174, 214, 255],
    5: [49, 130, 189, 255],
    6: [8, 81, 156, 255],
}


@dataclass(frozen=True)
class PublishResult:
    return_period: int
    item_id: str
    cog_path: Path
    item_json: Path
    tile_url: str


def _parse_return_periods(value: str | None) -> list[int]:
    if not value:
        return []
    out: list[int] = []
    for chunk in value.split(","):
        text = chunk.strip()
        if not text:
            continue
        out.append(int(text))
    return sorted(set(out))


def _default_collection_json_path() -> str:
    for candidate in DEFAULT_COLLECTION_JSON_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return ""


def _default_cog_root_path() -> str:
    env_value = os.getenv("COG_OUTPUT_DIR")
    if env_value:
        return env_value

    data_cogs = Path("/data/cogs")
    if data_cogs.exists() and os.access(data_cogs, os.W_OK):
        return str(data_cogs)

    return "raster-data/cogs"


def _run(cmd: list[str]) -> None:
    LOGGER.debug("Running command: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        output = proc.stdout.strip()
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{output[:4000]}"
        )


def _require_binary(name: str) -> None:
    from shutil import which

    if which(name) is None:
        raise RuntimeError(
            f"Required executable '{name}' was not found in PATH. "
            "Install GDAL tools in this runtime."
        )


def _load_mask_manifest(
    manifest_path: Path,
    return_period_filter: Iterable[int],
) -> dict[int, list[Path]]:
    allowed = set(return_period_filter)
    sources_by_rp: dict[int, list[Path]] = {}

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            status = str(row.get("status") or "").strip().lower()
            if status and status not in {"ok", "skipped_existing"}:
                continue

            rp_raw = row.get("return_period")
            path_raw = row.get("masked_file")
            if not rp_raw or not path_raw:
                continue

            try:
                rp = int(str(rp_raw).strip())
            except ValueError:
                continue

            if allowed and rp not in allowed:
                continue

            path = Path(path_raw).expanduser()
            if not path.exists():
                LOGGER.warning("Skipping missing masked file (rp=%s): %s", rp, path)
                continue

            sources_by_rp.setdefault(rp, []).append(path.resolve())

    for rp in list(sources_by_rp.keys()):
        unique_sorted = sorted(set(sources_by_rp[rp]))
        sources_by_rp[rp] = unique_sorted

    return sources_by_rp


def _format_nodata(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)


def _build_mosaic_cog(
    sources: list[Path],
    output_cog: Path,
    work_dir: Path,
    overwrite: bool,
) -> None:
    if not sources:
        raise ValueError("No source rasters provided for mosaicking.")

    _require_binary("gdalbuildvrt")
    _require_binary("gdal_translate")

    if output_cog.exists():
        if not overwrite:
            LOGGER.info("COG exists, skipping mosaic: %s", output_cog)
            return
        output_cog.unlink()

    work_dir.mkdir(parents=True, exist_ok=True)
    output_cog.parent.mkdir(parents=True, exist_ok=True)

    file_list = work_dir / "inputs.txt"
    vrt_path = work_dir / "mosaic.vrt"

    with open(file_list, "w", encoding="utf-8") as f_out:
        for src in sources:
            f_out.write(f"{src}\n")

    nodata_str = ""
    with rasterio.open(sources[0]) as ds:
        nodata_str = _format_nodata(ds.nodata)

    cmd_vrt = ["gdalbuildvrt", "-overwrite"]
    if nodata_str:
        cmd_vrt.extend(["-srcnodata", nodata_str, "-vrtnodata", nodata_str])
    cmd_vrt.extend(["-input_file_list", str(file_list), str(vrt_path)])
    _run(cmd_vrt)

    cmd_translate = [
        "gdal_translate",
        "-of",
        "COG",
        "-co",
        "COMPRESS=DEFLATE",
        "-co",
        "BLOCKSIZE=512",
        "-co",
        "OVERVIEWS=IGNORE_EXISTING",
        "-co",
        "RESAMPLING=NEAREST",
        "-co",
        "BIGTIFF=IF_SAFER",
    ]
    if nodata_str:
        cmd_translate.extend(["-a_nodata", nodata_str])
    cmd_translate.extend([str(vrt_path), str(output_cog)])
    _run(cmd_translate)



def _raster_meta(path: Path) -> dict[str, Any]:
    with rasterio.open(path) as ds:
        bounds_native = array_bounds(ds.height, ds.width, ds.transform)
        if ds.crs and ds.crs.to_epsg() != 4326:
            bbox = transform_bounds(ds.crs, "EPSG:4326", *bounds_native, densify_pts=21)
        else:
            bbox = bounds_native

        return {
            "bbox": [float(v) for v in bbox],
            "proj_epsg": ds.crs.to_epsg() if ds.crs else None,
            "proj_shape": [int(ds.height), int(ds.width)],
            "proj_transform": list(ds.transform),
            "nodata": ds.nodata,
            "dtype": str(ds.dtypes[0]),
        }


def _public_cog_href(cog_path: Path, cog_root: Path, public_prefix: str) -> str:
    try:
        rel = cog_path.resolve().relative_to(cog_root.resolve())
        return f"{public_prefix.rstrip('/')}/{rel.as_posix()}"
    except Exception:
        return f"{public_prefix.rstrip('/')}/{cog_path.name}"


def _preview_href(
    collection_id: str,
    item_id: str,
    titiler_prefix: str,
) -> str:
    params = {
        "assets": "data",
        "resampling": "nearest",
        "colormap": json.dumps(FLOOD_COLORMAP, separators=(",", ":")),
    }
    query = urlencode(params)
    return (
        f"{titiler_prefix.rstrip('/')}/collections/{collection_id}/items/{item_id}"
        f"/preview.png?{query}"
    )


def _tiles_href(
    collection_id: str,
    item_id: str,
    titiler_prefix: str,
) -> str:
    params = {
        "assets": "data",
        "resampling": "nearest",
        "colormap": json.dumps(FLOOD_COLORMAP, separators=(",", ":")),
    }
    query = urlencode(params)
    return (
        f"{titiler_prefix.rstrip('/')}/collections/{collection_id}/items/{item_id}"
        "/tiles/WebMercatorQuad/{z}/{x}/{y}.png"
        f"?{query}"
    )


def _build_stac_item(
    *,
    collection_id: str,
    item_id: str,
    return_period: int,
    cog_path: Path,
    cog_root: Path,
    public_cog_prefix: str,
    titiler_prefix: str,
    item_datetime: datetime,
) -> dict[str, Any]:
    meta = _raster_meta(cog_path)
    bbox = meta["bbox"]
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[2], bbox[3]],
            [bbox[0], bbox[3]],
            [bbox[0], bbox[1]],
        ]],
    }

    data_href = _public_cog_href(cog_path, cog_root, public_cog_prefix)
    preview = _preview_href(collection_id, item_id, titiler_prefix)

    iso_dt = item_datetime.replace(tzinfo=timezone.utc).isoformat()
    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": item_id,
        "collection": collection_id,
        "geometry": geometry,
        "bbox": bbox,
        "properties": {
            "datetime": iso_dt,
            "created": iso_dt,
            "return_period": return_period,
            "source": "JRC CEMS GLOFAS flood_hazard",
            "processing:permanent_water_masked": True,
            "proj:epsg": meta["proj_epsg"],
            "proj:shape": meta["proj_shape"],
            "proj:transform": meta["proj_transform"],
        },
        "links": [
            {
                "rel": "preview",
                "href": preview,
                "type": "image/png",
                "title": f"{item_id} preview",
            }
        ],
        "assets": {
            "data": {
                "href": data_href,
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "title": item_id,
                "roles": ["data"],
                "raster:bands": [
                    {
                        "data_type": meta["dtype"],
                        "nodata": meta["nodata"],
                    }
                ],
            },
            "thumbnail": {
                "href": preview,
                "type": "image/png",
                "title": f"{item_id} thumbnail",
                "roles": ["thumbnail", "overview"],
            },
        },
    }


def _wait_for_stac(base_url: str, retries: int = 20, sleep_seconds: int = 3) -> None:
    import time

    for i in range(retries):
        try:
            resp = requests.get(f"{base_url.rstrip('/')}/", timeout=15)
            if resp.status_code == 200:
                return
        except requests.RequestException:
            pass
        LOGGER.info("Waiting for STAC API (%d/%d)...", i + 1, retries)
        time.sleep(sleep_seconds)

    raise RuntimeError(f"STAC API not reachable: {base_url}")


def _upsert_collection(stac_api_url: str, collection_payload: dict[str, Any]) -> None:
    coll_id = collection_payload["id"]
    base = stac_api_url.rstrip("/")

    get_resp = requests.get(f"{base}/collections/{coll_id}", timeout=30)
    if get_resp.status_code == 200:
        resp = requests.put(
            f"{base}/collections/{coll_id}",
            json=collection_payload,
            timeout=60,
        )
    else:
        resp = requests.post(f"{base}/collections", json=collection_payload, timeout=60)

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Collection upsert failed ({resp.status_code}): {resp.text[:400]}"
        )


def _upsert_item(stac_api_url: str, collection_id: str, item_payload: dict[str, Any]) -> None:
    base = stac_api_url.rstrip("/")
    item_id = item_payload["id"]

    get_resp = requests.get(
        f"{base}/collections/{collection_id}/items/{item_id}",
        timeout=30,
    )
    if get_resp.status_code == 200:
        resp = requests.put(
            f"{base}/collections/{collection_id}/items/{item_id}",
            json=item_payload,
            timeout=60,
        )
    else:
        resp = requests.post(
            f"{base}/collections/{collection_id}/items",
            json=item_payload,
            timeout=60,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Item upsert failed for {item_id} ({resp.status_code}): {resp.text[:400]}"
        )



def _db_settings_from_env() -> dict[str, str]:
    settings = {
        "host": os.getenv("CMS_DB_HOST") or os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST") or "localhost",
        "port": os.getenv("CMS_DB_PORT") or os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432",
        "dbname": os.getenv("CMS_DB_NAME") or os.getenv("DB_NAME") or os.getenv("POSTGRES_DBNAME") or os.getenv("POSTGRES_DB") or "geomanager",
        "user": os.getenv("CMS_DB_USER") or os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or "postgres",
        "password": os.getenv("CMS_DB_PASSWORD") or os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASS") or os.getenv("POSTGRES_PASSWORD") or "",
    }
    return settings


def _get_dataset_id(cur, dataset_slug: str) -> str | None:
    cur.execute(
        """
        SELECT id
        FROM geomanager_dataset
        WHERE dataset_slug = %s
        ORDER BY modified DESC
        LIMIT 1
        """,
        (dataset_slug,),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    cur.execute(
        """
        SELECT id
        FROM geomanager_dataset
        WHERE lower(title) LIKE 'flood%extent%'
        ORDER BY modified DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    return None


def _find_existing_layer_ids(cur, dataset_id: str, title_exact: str, rp: int) -> list[tuple[str, str]]:
    cur.execute(
        """
        SELECT id, title
        FROM geomanager_rastertilelayer
        WHERE dataset_id = %s
          AND lower(title) = lower(%s)
        """,
        (dataset_id, title_exact),
    )
    rows = cur.fetchall()
    if rows:
        return [(str(r[0]), str(r[1])) for r in rows]

    cur.execute(
        """
        SELECT id, title
        FROM geomanager_rastertilelayer
        WHERE dataset_id = %s
          AND title ILIKE %s
          AND title ILIKE '%%return%%'
          AND title ILIKE '%%period%%'
        """,
        (dataset_id, f"%{rp}%"),
    )
    rows = cur.fetchall()
    return [(str(r[0]), str(r[1])) for r in rows]


def _insert_missing_layer(
    cur,
    *,
    dataset_id: str,
    title: str,
    base_url: str,
    rp: int,
) -> tuple[str, str]:
    cur.execute(
        """
        SELECT
            query_params_static,
            query_params_selectable,
            params_selectors_side_by_side,
            legend,
            more_info
        FROM geomanager_rastertilelayer
        WHERE dataset_id = %s
        ORDER BY "order" NULLS LAST, created ASC
        LIMIT 1
        """,
        (dataset_id,),
    )
    template = cur.fetchone()

    if template:
        query_params_static = json.dumps(template[0] if template[0] is not None else [])
        query_params_selectable = json.dumps(template[1] if template[1] is not None else [])
        params_side = bool(template[2])
        legend = json.dumps(template[3] if template[3] is not None else [])
        more_info = json.dumps(template[4] if template[4] is not None else [])
    else:
        query_params_static = "[]"
        query_params_selectable = "[]"
        params_side = False
        legend = "[]"
        more_info = "[]"

    cur.execute(
        """
        SELECT COALESCE(MAX("order"), -1)
        FROM geomanager_rastertilelayer
        WHERE dataset_id = %s
        """,
        (dataset_id,),
    )
    max_order = int(cur.fetchone()[0] or -1)
    order = 0 if rp == 25 else max_order + 1

    layer_id = str(uuid.uuid4())
    is_default = rp == 25 and max_order < 0

    cur.execute(
        """
        INSERT INTO geomanager_rastertilelayer (
            id, created, modified, title, "default",
            base_url, get_time_from_tile_json, tile_json_url,
            timestamps_response_object_key, date_format,
            time_parameter_name, dataset_id,
            query_params_static, query_params_selectable,
            params_selectors_side_by_side, legend, more_info, "order"
        ) VALUES (
            %s, NOW(), NOW(), %s, %s,
            %s, FALSE, NULL,
            NULL, NULL,
            NULL, %s,
            %s::jsonb, %s::jsonb,
            %s, %s::jsonb, %s::jsonb, %s
        )
        """,
        (
            layer_id,
            title,
            is_default,
            base_url,
            dataset_id,
            query_params_static,
            query_params_selectable,
            params_side,
            legend,
            more_info,
            order,
        ),
    )
    return layer_id, title


def _update_cms_layers(
    *,
    dataset_slug: str,
    tile_urls_by_rp: dict[int, str],
    create_missing_layers: bool,
    dry_run: bool,
) -> list[dict[str, Any]]:
    db = _db_settings_from_env()
    LOGGER.info(
        "Updating CMS raster tile URLs in %s:%s/%s",
        db["host"],
        db["port"],
        db["dbname"],
    )

    updates: list[dict[str, Any]] = []

    conn = psycopg2.connect(**db)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            dataset_id = _get_dataset_id(cur, dataset_slug)
            if not dataset_id:
                raise RuntimeError(
                    f"Could not find dataset slug '{dataset_slug}' in geomanager_dataset."
                )

            cur.execute(
                """
                UPDATE geomanager_dataset
                SET layer_type = 'raster_tile', modified = NOW()
                WHERE id = %s
                  AND layer_type <> 'raster_tile'
                """,
                (dataset_id,),
            )

            for rp, url in sorted(tile_urls_by_rp.items()):
                title_exact = f"{rp}-year return period"
                existing = _find_existing_layer_ids(cur, dataset_id, title_exact, rp)

                if existing:
                    for layer_id, _layer_title in existing:
                        cur.execute(
                            """
                            UPDATE geomanager_rastertilelayer
                            SET base_url = %s,
                                modified = NOW()
                            WHERE id = %s::uuid
                            """,
                            (url, layer_id),
                        )
                    for layer_id, layer_title in existing:
                        updates.append(
                            {
                                "return_period": rp,
                                "layer_id": layer_id,
                                "layer_title": layer_title,
                                "action": "updated",
                                "base_url": url,
                            }
                        )
                    continue

                if not create_missing_layers:
                    LOGGER.warning(
                        "No raster tile layer found for RP%s in dataset %s (title '%s').",
                        rp,
                        dataset_slug,
                        title_exact,
                    )
                    updates.append(
                        {
                            "return_period": rp,
                            "layer_id": None,
                            "layer_title": title_exact,
                            "action": "missing",
                            "base_url": url,
                        }
                    )
                    continue

                layer_id, layer_title = _insert_missing_layer(
                    cur,
                    dataset_id=dataset_id,
                    title=title_exact,
                    base_url=url,
                    rp=rp,
                )
                updates.append(
                    {
                        "return_period": rp,
                        "layer_id": layer_id,
                        "layer_title": layer_title,
                        "action": "inserted",
                        "base_url": url,
                    }
                )

            if dry_run:
                conn.rollback()
            else:
                conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return updates


def _write_publish_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=[
                "return_period",
                "item_id",
                "cog_path",
                "item_json",
                "tile_url",
                "cms_action",
                "cms_layer_id",
                "cms_layer_title",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish JRC masked flood-hazard rasters to STAC and update CMS/mapviewer tile URLs."
        )
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to manifest.csv produced by jrc_flood_hazard_mask.py",
    )
    parser.add_argument(
        "--work-dir",
        default="gpr/jrc_publish",
        help="Working directory for VRT files and publish manifest output",
    )
    parser.add_argument(
        "--cog-root",
        default=_default_cog_root_path(),
        help="COG output root directory (served by /stac-cogs)",
    )
    parser.add_argument(
        "--cog-subdir",
        default="flood-extent",
        help="COG output subdirectory under --cog-root",
    )
    parser.add_argument(
        "--item-date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="Date stamp for item IDs and datetime property (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--return-periods",
        default="",
        help="Optional comma-separated return periods to publish (e.g. 25,100)",
    )
    parser.add_argument(
        "--collection-id",
        default=DEFAULT_COLLECTION_ID,
        help="STAC collection ID",
    )
    parser.add_argument(
        "--collection-json",
        default=_default_collection_json_path(),
        help=(
            "Optional STAC collection JSON file to upsert before item publish. "
            "If missing, item upsert assumes collection already exists."
        ),
    )
    parser.add_argument(
        "--stac-api-url",
        default=DEFAULT_STAC_API_URL,
        help="STAC API base URL",
    )
    parser.add_argument(
        "--stac-cog-public-prefix",
        default=DEFAULT_STAC_COG_PREFIX,
        help="Public prefix for COG hrefs in STAC items",
    )
    parser.add_argument(
        "--titiler-public-prefix",
        default=DEFAULT_TITILER_PREFIX,
        help="Public prefix for TiTiler endpoints",
    )
    parser.add_argument(
        "--cms-dataset-slug",
        default=DEFAULT_DATASET_SLUG,
        help="Dataset slug in CMS for flood extent raster tile layers",
    )
    parser.add_argument(
        "--create-missing-layers",
        action="store_true",
        help="Create missing geomanager_rastertilelayer rows when RP layer is absent",
    )
    parser.add_argument(
        "--skip-stac",
        action="store_true",
        help="Skip STAC collection/item upsert",
    )
    parser.add_argument(
        "--skip-cms",
        action="store_true",
        help="Skip CMS raster tile URL updates",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing COGs and item sidecars",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned outputs; do not write STAC/CMS changes",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    args = parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    cog_root = Path(args.cog_root).expanduser().resolve()
    cog_subdir = str(args.cog_subdir).strip("/")

    try:
        item_date = datetime.strptime(args.item_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise SystemExit(f"Invalid --item-date '{args.item_date}': {exc}")

    rp_filter = _parse_return_periods(args.return_periods)
    sources_by_rp = _load_mask_manifest(manifest_path, rp_filter)
    if not sources_by_rp:
        LOGGER.error("No eligible masked files found in %s", manifest_path)
        return 1

    LOGGER.info("Return periods to publish: %s", sorted(sources_by_rp.keys()))

    published: list[PublishResult] = []

    for rp, sources in sorted(sources_by_rp.items()):
        item_id = f"jrc_rp{rp}_masked_{item_date.strftime('%Y%m%d')}"
        cog_path = cog_root / cog_subdir / f"{item_id}.tif"
        item_json = cog_path.with_suffix(".json")

        LOGGER.info("Building RP%s mosaic from %d tiles", rp, len(sources))
        if not args.dry_run:
            rp_work_dir = work_dir / f"rp_{rp}"
            _build_mosaic_cog(
                sources=sources,
                output_cog=cog_path,
                work_dir=rp_work_dir,
                overwrite=args.overwrite,
            )

            item_payload = _build_stac_item(
                collection_id=args.collection_id,
                item_id=item_id,
                return_period=rp,
                cog_path=cog_path,
                cog_root=cog_root,
                public_cog_prefix=args.stac_cog_public_prefix,
                titiler_prefix=args.titiler_public_prefix,
                item_datetime=item_date,
            )
            item_json.parent.mkdir(parents=True, exist_ok=True)
            with open(item_json, "w", encoding="utf-8") as f_out:
                json.dump(item_payload, f_out, indent=2)
        else:
            item_json.parent.mkdir(parents=True, exist_ok=True)
            item_payload = {
                "id": item_id,
                "collection": args.collection_id,
            }

        tile_url = _tiles_href(args.collection_id, item_id, args.titiler_public_prefix)
        published.append(
            PublishResult(
                return_period=rp,
                item_id=item_id,
                cog_path=cog_path,
                item_json=item_json,
                tile_url=tile_url,
            )
        )

        if not args.skip_stac and not args.dry_run:
            _wait_for_stac(args.stac_api_url)
            collection_json = str(args.collection_json).strip()
            if collection_json:
                collection_path = Path(collection_json).expanduser().resolve()
                if collection_path.exists():
                    with open(collection_path, encoding="utf-8") as f_in:
                        collection_payload = json.load(f_in)
                    _upsert_collection(args.stac_api_url, collection_payload)
                else:
                    LOGGER.warning("Collection JSON not found, skipping upsert: %s", collection_path)

            _upsert_item(args.stac_api_url, args.collection_id, item_payload)
            LOGGER.info("Upserted STAC item: %s", item_id)

    cms_rows: dict[int, dict[str, Any]] = {}
    if not args.skip_cms:
        tile_urls_by_rp = {result.return_period: result.tile_url for result in published}
        updates = _update_cms_layers(
            dataset_slug=args.cms_dataset_slug,
            tile_urls_by_rp=tile_urls_by_rp,
            create_missing_layers=args.create_missing_layers,
            dry_run=args.dry_run,
        )
        for row in updates:
            cms_rows[int(row["return_period"])] = row

    publish_rows: list[dict[str, Any]] = []
    for result in published:
        cms = cms_rows.get(result.return_period, {})
        publish_rows.append(
            {
                "return_period": result.return_period,
                "item_id": result.item_id,
                "cog_path": str(result.cog_path),
                "item_json": str(result.item_json),
                "tile_url": result.tile_url,
                "cms_action": cms.get("action", "skipped" if args.skip_cms else "n/a"),
                "cms_layer_id": cms.get("layer_id", ""),
                "cms_layer_title": cms.get("layer_title", ""),
            }
        )

    out_manifest = work_dir / "publish_manifest.csv"
    _write_publish_manifest(out_manifest, publish_rows)
    LOGGER.info("Wrote publish manifest: %s", out_manifest)

    LOGGER.info(
        "Completed JRC publish pipeline. items=%d stac=%s cms=%s dry_run=%s",
        len(published),
        not args.skip_stac,
        not args.skip_cms,
        args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
