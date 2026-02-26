#!/usr/bin/env python3
"""Convert static raster files to Cloud Optimized GeoTIFFs and generate STAC Item JSON sidecars.

Converts flood-extent return periods, LandScan population, and ASAP land-cover
rasters into COGs with DEFLATE compression and 512x512 block size, then writes
a STAC Item JSON file for each output COG.

Usage:
    python convert_static_cogs.py --input-dir /data/rasters --output-dir /data/cogs
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import click
import pystac
import rasterio
from rasterio.transform import array_bounds
from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles
from shapely.geometry import box, mapping

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping from source file to output location and STAC collection
# ---------------------------------------------------------------------------
FILE_MAP = {
    "return_periods/M6_25y_clipped.tif": {
        "output_subdir": "flood-extent",
        "output_name": "M6_25y.tif",
        "item_id": "M6_25y",
        "collection": "flood-extent-return-periods",
        "title": "25-Year Flood Extent Return Period",
        "description": "Flood extent for the 25-year return period (M6 model), Greater Horn of Africa.",
    },
    "return_periods/M6_100y_clipped.tif": {
        "output_subdir": "flood-extent",
        "output_name": "M6_100y.tif",
        "item_id": "M6_100y",
        "collection": "flood-extent-return-periods",
        "title": "100-Year Flood Extent Return Period",
        "description": "Flood extent for the 100-year return period (M6 model), Greater Horn of Africa.",
    },
    "population/landscan_population_2024.tif": {
        "output_subdir": "population",
        "output_name": "landscan_2024.tif",
        "item_id": "landscan_2024",
        "collection": "landscan-population",
        "title": "LandScan Population 2024",
        "description": "LandScan global population dataset for 2024, clipped to Greater Horn of Africa.",
    },
    "landcover/asap_cropland_gha.tif": {
        "output_subdir": "landcover",
        "output_name": "asap_cropland.tif",
        "item_id": "asap_cropland",
        "collection": "asap-cropland",
        "title": "ASAP Cropland",
        "description": "ASAP cropland mask for the Greater Horn of Africa.",
    },
    "landcover/asap_rangeland_gha.tif": {
        "output_subdir": "landcover",
        "output_name": "asap_rangeland.tif",
        "item_id": "asap_rangeland",
        "collection": "asap-rangeland",
        "title": "ASAP Rangeland",
        "description": "ASAP rangeland mask for the Greater Horn of Africa.",
    },
}


def _should_skip(input_path: Path, output_path: Path) -> bool:
    """Return True if the output COG exists and is newer than the input file."""
    if not output_path.exists():
        return False
    return output_path.stat().st_mtime >= input_path.stat().st_mtime


def convert_to_cog(input_path: Path, output_path: Path) -> None:
    """Translate *input_path* to a Cloud Optimized GeoTIFF at *output_path*.

    Uses DEFLATE compression, 512x512 block size, and preserves the original CRS.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_profile = cog_profiles.get("deflate")
    output_profile.update(
        blockxsize=512,
        blockysize=512,
    )

    config = {
        "GDAL_NUM_THREADS": "ALL_CPUS",
        "GDAL_TIFF_INTERNAL_MASK": True,
        "GDAL_TIFF_OVR_BLOCKSIZE": 512,
    }

    cog_translate(
        str(input_path),
        str(output_path),
        output_profile,
        config=config,
        in_memory=False,
        quiet=False,
        overview_level=6,
        overview_resampling="nearest",
        use_cog_driver=True,
    )

    logger.info("Created COG: %s", output_path)


def validate_cog(cog_path: Path) -> bool:
    """Validate that *cog_path* is a valid Cloud Optimized GeoTIFF.

    Returns True if valid, False otherwise.
    """
    is_valid, errors, warnings = cog_validate(str(cog_path))
    if warnings:
        for w in warnings:
            logger.warning("COG validation warning (%s): %s", cog_path.name, w)
    if not is_valid:
        for e in errors:
            logger.error("COG validation error (%s): %s", cog_path.name, e)
    return is_valid


def _get_raster_metadata(raster_path: Path) -> dict:
    """Read spatial metadata from a raster file.

    Returns a dict with keys: bbox, geometry, crs, width, height, dtype, nodata.
    """
    with rasterio.open(raster_path) as src:
        bounds = src.bounds
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
        geom = mapping(box(*bbox))
        return {
            "bbox": bbox,
            "geometry": geom,
            "crs": src.crs.to_epsg() or 4326,
            "width": src.width,
            "height": src.height,
            "dtype": src.dtypes[0],
            "nodata": src.nodata,
            "transform": list(src.transform),
            "band_count": src.count,
        }


def create_stac_item(
    cog_path: Path,
    output_dir: Path,
    item_id: str,
    collection_id: str,
    title: str,
    description: str,
    container_cog_href: str,
) -> Path:
    """Create a STAC Item JSON file for the given COG.

    Parameters
    ----------
    cog_path : Path
        Local path to the COG file (used to read metadata).
    output_dir : Path
        Directory where the JSON sidecar will be written (``items/`` subdirectory).
    item_id : str
        Unique STAC Item identifier.
    collection_id : str
        STAC Collection this item belongs to.
    title : str
        Human-readable title for the item.
    description : str
        Short description of the dataset.
    container_cog_href : str
        Asset href as it will be resolved inside the container (e.g.
        ``/data/cogs/flood-extent/M6_25y.tif``).

    Returns
    -------
    Path
        Path to the written JSON file.
    """
    meta = _get_raster_metadata(cog_path)

    # Use file modification time as the item datetime for static layers
    file_mtime = datetime.fromtimestamp(cog_path.stat().st_mtime, tz=timezone.utc)

    item = pystac.Item(
        id=item_id,
        geometry=meta["geometry"],
        bbox=meta["bbox"],
        datetime=file_mtime,
        properties={
            "title": title,
            "description": description,
            "proj:epsg": meta["crs"],
            "proj:shape": [meta["height"], meta["width"]],
            "proj:transform": meta["transform"],
        },
    )

    item.common_metadata.created = datetime.now(tz=timezone.utc)

    # Link to collection
    item.collection_id = collection_id

    # Add the COG asset
    asset = pystac.Asset(
        href=container_cog_href,
        media_type=pystac.MediaType.COG,
        roles=["data"],
        title=title,
        extra_fields={
            "raster:bands": [
                {
                    "data_type": meta["dtype"],
                    "nodata": meta["nodata"],
                }
            ],
        },
    )
    item.add_asset("data", asset)

    # Write to items/ directory
    items_dir = output_dir / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    json_path = items_dir / f"{item_id}.json"

    item_dict = item.to_dict()
    with open(json_path, "w") as f:
        json.dump(item_dict, f, indent=2, default=str)

    logger.info("Created STAC Item: %s", json_path)
    return json_path


@click.command()
@click.option(
    "--input-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("/data/rasters"),
    show_default=True,
    help="Root directory containing source raster files.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/data/cogs"),
    show_default=True,
    help="Root directory for output COGs and STAC items.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Re-convert even if the output COG is newer than the input.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be done without writing any files.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging.",
)
def main(input_dir: Path, output_dir: Path, force: bool, dry_run: bool, verbose: bool):
    """Convert static raster files to Cloud Optimized GeoTIFFs and create STAC Item JSON sidecars."""

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {"converted": 0, "skipped": 0, "failed": 0, "items_created": 0}

    for rel_input, info in FILE_MAP.items():
        src = input_dir / rel_input
        if not src.exists():
            logger.warning("Source file not found, skipping: %s", src)
            stats["failed"] += 1
            continue

        cog_path = output_dir / info["output_subdir"] / info["output_name"]
        container_href = f"/data/cogs/{info['output_subdir']}/{info['output_name']}"

        # --- COG conversion ------------------------------------------------
        if not force and _should_skip(src, cog_path):
            logger.info("Skipping (output newer than input): %s", cog_path)
            stats["skipped"] += 1
        else:
            if dry_run:
                logger.info("[DRY-RUN] Would convert: %s -> %s", src, cog_path)
                stats["converted"] += 1
                continue
            try:
                logger.info("Converting %s -> %s", src, cog_path)
                convert_to_cog(src, cog_path)
                stats["converted"] += 1
            except Exception:
                logger.exception("Failed to convert %s", src)
                stats["failed"] += 1
                continue

            # Validate
            if not validate_cog(cog_path):
                logger.error("COG validation failed for %s — file kept but may be invalid", cog_path)

        # --- STAC Item JSON ------------------------------------------------
        if dry_run:
            logger.info("[DRY-RUN] Would create STAC item: %s", info["item_id"])
            stats["items_created"] += 1
            continue

        try:
            create_stac_item(
                cog_path=cog_path,
                output_dir=output_dir,
                item_id=info["item_id"],
                collection_id=info["collection"],
                title=info["title"],
                description=info["description"],
                container_cog_href=container_href,
            )
            stats["items_created"] += 1
        except Exception:
            logger.exception("Failed to create STAC item for %s", info["item_id"])
            stats["failed"] += 1

    # --- Summary -----------------------------------------------------------
    logger.info(
        "Done. Converted: %d | Skipped: %d | Items created: %d | Errors: %d",
        stats["converted"],
        stats["skipped"],
        stats["items_created"],
        stats["failed"],
    )


if __name__ == "__main__":
    main()
