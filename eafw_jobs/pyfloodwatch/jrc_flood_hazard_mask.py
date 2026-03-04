"""JRC GloFAS flood hazard downloader + permanent-water masking utility.

This script:
1) selects JRC flood-hazard tiles intersecting a region of interest (ROI),
2) downloads hazard and permanent-water GeoTIFFs,
3) masks permanent water from hazard rasters,
4) writes a manifest CSV for downstream ingest to STAC/TiTiler/PostGIS.

Data source:
https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/

Notes:
- By default this uses the *_depth_reclass.tif files.
- If you need continuous depth values, use --raw-depth.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.warp import reproject

LOGGER = logging.getLogger("jrc_flood_hazard_mask")

JRC_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard"
)
TILE_INDEX_URL = f"{JRC_BASE_URL}/tile_extents.geojson"

DEFAULT_GHOA_BBOX = {
    "min_lon": 19.0,
    "min_lat": -8.0,
    "max_lon": 53.0,
    "max_lat": 23.0,
}
DEFAULT_RETURN_PERIODS = [100]


@dataclass(frozen=True)
class HazardTile:
    tile_id: int
    tile_name: str
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @property
    def tile_code(self) -> str:
        return f"ID{self.tile_id}_{self.tile_name}"


def _bbox_intersects(a: dict[str, float], b: dict[str, float]) -> bool:
    return not (
        a["max_lon"] < b["min_lon"]
        or a["min_lon"] > b["max_lon"]
        or a["max_lat"] < b["min_lat"]
        or a["min_lat"] > b["max_lat"]
    )


def _extract_bbox_from_polygon_coords(coords: list[list[list[float]]]) -> dict[str, float]:
    ring = coords[0] if coords else []
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return {
        "min_lon": min(lons),
        "min_lat": min(lats),
        "max_lon": max(lons),
        "max_lat": max(lats),
    }


def fetch_tile_index(tile_index_url: str = TILE_INDEX_URL, timeout: int = 120) -> list[HazardTile]:
    LOGGER.info("Fetching tile index: %s", tile_index_url)
    response = requests.get(tile_index_url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    tiles: list[HazardTile] = []
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue

        tile_id = props.get("id")
        tile_name = props.get("name")
        if tile_id is None or not tile_name:
            continue

        bbox = _extract_bbox_from_polygon_coords(geom.get("coordinates", []))
        tiles.append(
            HazardTile(
                tile_id=int(tile_id),
                tile_name=str(tile_name),
                min_lon=bbox["min_lon"],
                min_lat=bbox["min_lat"],
                max_lon=bbox["max_lon"],
                max_lat=bbox["max_lat"],
            )
        )
    return tiles


def select_tiles_for_roi(tiles: Iterable[HazardTile], roi_bbox: dict[str, float]) -> list[HazardTile]:
    selected = []
    for tile in tiles:
        tile_bbox = {
            "min_lon": tile.min_lon,
            "min_lat": tile.min_lat,
            "max_lon": tile.max_lon,
            "max_lat": tile.max_lat,
        }
        if _bbox_intersects(tile_bbox, roi_bbox):
            selected.append(tile)
    selected.sort(key=lambda item: item.tile_id)
    return selected


def _download_file(url: str, dst_path: Path, overwrite: bool = False, timeout: int = 180) -> bool:
    if dst_path.exists() and not overwrite:
        return False

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with open(dst_path, "wb") as f_out:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f_out.write(chunk)
    return True


def _choose_output_nodata(dtype: np.dtype, source_nodata):
    if source_nodata is not None:
        return source_nodata
    if np.issubdtype(dtype, np.floating):
        return np.nan
    if np.issubdtype(dtype, np.unsignedinteger):
        return np.iinfo(dtype).max
    if np.issubdtype(dtype, np.signedinteger):
        return np.iinfo(dtype).min
    return 0


def mask_hazard_with_permanent_water(
    hazard_path: Path,
    permanent_water_path: Path,
    out_path: Path,
    overwrite: bool = False,
) -> int:
    if out_path.exists() and not overwrite:
        return -1

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(hazard_path) as hazard_ds, rasterio.open(permanent_water_path) as water_ds:
        hazard = hazard_ds.read(1)
        water = water_ds.read(1)

        # Align permanent-water raster to hazard grid if needed.
        if (
            hazard_ds.shape != water_ds.shape
            or hazard_ds.transform != water_ds.transform
            or hazard_ds.crs != water_ds.crs
        ):
            aligned = np.zeros(hazard_ds.shape, dtype=water.dtype)
            reproject(
                source=water,
                destination=aligned,
                src_transform=water_ds.transform,
                src_crs=water_ds.crs,
                dst_transform=hazard_ds.transform,
                dst_crs=hazard_ds.crs,
                resampling=Resampling.nearest,
            )
            water = aligned
            water_nodata = None
        else:
            water_nodata = water_ds.nodata

        water_valid = np.ones(water.shape, dtype=bool)
        if water_nodata is not None:
            water_valid = water != water_nodata
        permanent_water_mask = water_valid & (water > 0)

        out = hazard.copy()
        out_nodata = _choose_output_nodata(out.dtype, hazard_ds.nodata)
        out[permanent_water_mask] = out_nodata

        profile = hazard_ds.profile.copy()
        profile.update(
            nodata=out_nodata,
            compress="deflate",
            predictor=2 if np.issubdtype(out.dtype, np.integer) else 3,
            tiled=True,
        )

        with rasterio.open(out_path, "w", **profile) as out_ds:
            out_ds.write(out, 1)

    return int(permanent_water_mask.sum())


def _parse_return_periods(value: str) -> list[int]:
    parsed = []
    for chunk in value.split(","):
        text = chunk.strip()
        if not text:
            continue
        parsed.append(int(text))
    if not parsed:
        raise ValueError("At least one return period is required.")
    return sorted(set(parsed))


def _build_paths(
    base_dir: Path,
    tile: HazardTile,
    return_period: int,
    use_reclass: bool,
) -> tuple[str, str, Path, Path, Path]:
    rp = f"RP{return_period}"
    suffix = "_depth_reclass.tif" if use_reclass else "_depth.tif"

    hazard_name = f"{tile.tile_code}_{rp}{suffix}"
    water_name = f"{tile.tile_code}_permanent_water.tif"

    hazard_url = f"{JRC_BASE_URL}/{rp}/{hazard_name}"
    water_url = f"{JRC_BASE_URL}/Permanent_WaterBodies/{water_name}"

    hazard_local = base_dir / "downloads" / rp / hazard_name
    water_local = base_dir / "downloads" / "Permanent_WaterBodies" / water_name
    masked_local = base_dir / "masked" / rp / hazard_name.replace(".tif", "_masked.tif")

    return hazard_url, water_url, hazard_local, water_local, masked_local


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download JRC flood hazard tiles and mask permanent water."
    )
    parser.add_argument("--min-lon", type=float, default=DEFAULT_GHOA_BBOX["min_lon"])
    parser.add_argument("--min-lat", type=float, default=DEFAULT_GHOA_BBOX["min_lat"])
    parser.add_argument("--max-lon", type=float, default=DEFAULT_GHOA_BBOX["max_lon"])
    parser.add_argument("--max-lat", type=float, default=DEFAULT_GHOA_BBOX["max_lat"])
    parser.add_argument(
        "--return-periods",
        type=str,
        default=",".join(str(v) for v in DEFAULT_RETURN_PERIODS),
        help="Comma-separated list, e.g. 10,20,50,100",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="gpr/jrc_flood_hazard_masked",
        help="Output directory for downloads, masked rasters, and manifest.csv",
    )
    parser.add_argument(
        "--raw-depth",
        action="store_true",
        help="Use *_depth.tif instead of *_depth_reclass.tif",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--publish",
        action="store_true",
        help=(
            "After masking, run jrc_stac_publish.py to publish to STAC and update CMS/mapviewer."
        ),
    )
    parser.add_argument(
        "--publish-work-dir",
        type=str,
        default="gpr/jrc_publish",
        help="Work/output directory for jrc_stac_publish.py when --publish is used.",
    )
    parser.add_argument(
        "--publish-skip-stac",
        action="store_true",
        help="Pass --skip-stac to jrc_stac_publish.py when --publish is used.",
    )
    parser.add_argument(
        "--publish-skip-cms",
        action="store_true",
        help="Pass --skip-cms to jrc_stac_publish.py when --publish is used.",
    )
    parser.add_argument(
        "--tile-index-url",
        type=str,
        default=TILE_INDEX_URL,
        help="Override tile_extents.geojson URL",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    args = parse_args()
    roi_bbox = {
        "min_lon": args.min_lon,
        "min_lat": args.min_lat,
        "max_lon": args.max_lon,
        "max_lat": args.max_lat,
    }
    return_periods = _parse_return_periods(args.return_periods)
    out_root = Path(args.output_dir).resolve()
    use_reclass = not args.raw_depth

    LOGGER.info("ROI bbox: %s", roi_bbox)
    LOGGER.info("Return periods: %s", return_periods)
    LOGGER.info("Using hazard product: %s", "depth_reclass" if use_reclass else "depth")
    LOGGER.info("Output dir: %s", out_root)

    all_tiles = fetch_tile_index(args.tile_index_url)
    selected_tiles = select_tiles_for_roi(all_tiles, roi_bbox)
    if not selected_tiles:
        LOGGER.warning("No JRC tiles intersect this ROI.")
        return 0

    LOGGER.info("Selected %d intersecting tiles.", len(selected_tiles))

    tasks = []
    for tile in selected_tiles:
        for rp in return_periods:
            tasks.append((tile, rp))

    manifest_rows: list[dict[str, str | int]] = []

    if args.dry_run:
        for tile, rp in tasks:
            hazard_url, water_url, hazard_local, water_local, masked_local = _build_paths(
                out_root, tile, rp, use_reclass
            )
            manifest_rows.append(
                {
                    "tile_id": tile.tile_id,
                    "tile_name": tile.tile_name,
                    "return_period": rp,
                    "hazard_url": hazard_url,
                    "water_url": water_url,
                    "hazard_file": str(hazard_local),
                    "water_file": str(water_local),
                    "masked_file": str(masked_local),
                    "masked_pixels": "",
                    "status": "dry_run",
                    "error": "",
                }
            )
    else:
        def _run_one(tile: HazardTile, rp: int) -> dict[str, str | int]:
            hazard_url, water_url, hazard_local, water_local, masked_local = _build_paths(
                out_root, tile, rp, use_reclass
            )
            row = {
                "tile_id": tile.tile_id,
                "tile_name": tile.tile_name,
                "return_period": rp,
                "hazard_url": hazard_url,
                "water_url": water_url,
                "hazard_file": str(hazard_local),
                "water_file": str(water_local),
                "masked_file": str(masked_local),
                "masked_pixels": "",
                "status": "ok",
                "error": "",
            }
            try:
                _download_file(hazard_url, hazard_local, overwrite=args.overwrite)
                _download_file(water_url, water_local, overwrite=args.overwrite)
                masked_count = mask_hazard_with_permanent_water(
                    hazard_local, water_local, masked_local, overwrite=args.overwrite
                )
                if masked_count >= 0:
                    row["masked_pixels"] = masked_count
                else:
                    row["masked_pixels"] = "skipped_existing"
            except Exception as exc:
                row["status"] = "failed"
                row["error"] = str(exc)
            return row

        with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
            futures = [pool.submit(_run_one, tile, rp) for tile, rp in tasks]
            for future in as_completed(futures):
                row = future.result()
                manifest_rows.append(row)
                if row["status"] == "ok":
                    LOGGER.info(
                        "Processed tile=%s rp=%s masked=%s",
                        row["tile_name"],
                        row["return_period"],
                        row["masked_pixels"],
                    )
                else:
                    LOGGER.error(
                        "Failed tile=%s rp=%s error=%s",
                        row["tile_name"],
                        row["return_period"],
                        row["error"],
                    )

    out_root.mkdir(parents=True, exist_ok=True)
    manifest_path = out_root / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=[
                "tile_id",
                "tile_name",
                "return_period",
                "hazard_url",
                "water_url",
                "hazard_file",
                "water_file",
                "masked_file",
                "masked_pixels",
                "status",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(sorted(manifest_rows, key=lambda row: (row["tile_id"], row["return_period"])))

    ok = sum(1 for row in manifest_rows if row["status"] == "ok")
    failed = sum(1 for row in manifest_rows if row["status"] == "failed")
    LOGGER.info("Done. ok=%d failed=%d manifest=%s", ok, failed, manifest_path)

    publish_cmd = [
        sys.executable,
        str(Path(__file__).resolve().with_name("jrc_stac_publish.py")),
        "--manifest",
        str(manifest_path),
        "--work-dir",
        str(Path(args.publish_work_dir).resolve()),
        "--return-periods",
        ",".join(str(v) for v in return_periods),
    ]
    if args.overwrite:
        publish_cmd.append("--overwrite")
    if args.publish_skip_stac:
        publish_cmd.append("--skip-stac")
    if args.publish_skip_cms:
        publish_cmd.append("--skip-cms")

    if args.publish and not args.dry_run and failed == 0:
        LOGGER.info("Running publish step: %s", " ".join(publish_cmd))
        try:
            subprocess.run(publish_cmd, check=True)
        except subprocess.CalledProcessError as exc:
            LOGGER.error("Publish step failed with exit code %s", exc.returncode)
            return exc.returncode or 1
    else:
        LOGGER.info("Next step (manual publish): %s", " ".join(publish_cmd))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
