#!/usr/bin/env python3
"""
COG Conversion Utility for FloodWatch (EAFW).

Converts GeoTIFFs to Cloud Optimized GeoTIFFs, validates output,
and generates STAC Item JSON sidecars.

Usage:
    python cog_convert.py single data/mapfiles/data/landcover/asap_cropland_gha.tif
    python cog_convert.py batch data/mapfiles/data/ --output-dir /data/cogs
    python cog_convert.py validate /data/cogs/landcover/asap_cropland_gha.tif
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import click
import rasterio
from rasterio.transform import array_bounds
from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles
from shapely.geometry import box, mapping

try:
    from .cog_utils import (
        GHA_BBOX,
        STYLE_PRESETS,
        build_titiler_preview_href,
        public_cog_href,
    )
except ImportError:
    # Running as a standalone script (python cog_convert.py …)
    from cog_utils import (  # type: ignore[import-untyped]
        GHA_BBOX,
        STYLE_PRESETS,
        build_titiler_preview_href,
        public_cog_href,
    )

logger = logging.getLogger("cog_convert")

DEFAULT_OUTPUT_ROOT = Path("/data/cogs")
COG_PROFILE = "deflate"
COG_BLOCKSIZE = 512
OVERVIEW_RESAMPLING = "nearest"

def _resolve_output_path(src_path: Path, output_dir: Optional[Path]) -> Path:
    stem = src_path.stem
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{stem}.tif"
    return src_path.with_name(f"{stem}_cog.tif")


def convert_to_cog(
    src_path: Path,
    dst_path: Path,
    profile_name: str = COG_PROFILE,
    blocksize: int = COG_BLOCKSIZE,
    overview_resampling: str = OVERVIEW_RESAMPLING,
    nodata: Optional[float] = None,
) -> Path:
    """Convert src_path to a Cloud Optimized GeoTIFF at dst_path."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    profile = cog_profiles.get(profile_name)
    profile.update(blockxsize=blocksize, blockysize=blocksize)

    config = {
        "GDAL_TIFF_INTERNAL_MASK": True,
        "GDAL_TIFF_OVR_BLOCKSIZE": blocksize,
    }

    output_profile = profile.copy()
    if nodata is not None:
        output_profile["nodata"] = nodata

    cog_translate(
        str(src_path),
        str(dst_path),
        output_profile,
        overview_resampling=overview_resampling,
        config=config,
        in_memory=False,
        quiet=False,
    )
    logger.info("COG written: %s", dst_path)
    return dst_path


def validate_cog(path: Path) -> bool:
    """Return True if path is a valid COG."""
    is_valid, errors, warnings = cog_validate(str(path))
    for w in warnings:
        logger.warning("COG warning [%s]: %s", path.name, w)
    for e in errors:
        logger.error("COG error [%s]: %s", path.name, e)
    return is_valid


def _guess_collection(src_path: Path) -> str:
    """Infer collection from raster path/filename without fixed file lists."""
    path = "/".join(p.lower() for p in src_path.parts)
    name = src_path.name.lower()

    if "cmorph" in path or "virtualizarr" in path:
        return "cmorph-30min-virtualizarr-parquet"
    if "wrf" in path or "rainfall" in path:
        return "wrf-daily-rainfall"
    if "multimodal" in path:
        if "whca" in path or "nile" in path:
            return "multimodal-points-whca"
        return "multimodal-points-gha"
    if "cropland" in path or "cropland" in name:
        return "asap-cropland"
    if "rangeland" in path or "rangeland" in name:
        return "asap-rangeland"
    if "landscan" in path or "population" in path:
        return "landscan-population"
    if "return_period" in path or "25y" in name or "100y" in name:
        return "flood-extent-return-periods"

    # Generic fallback: derive collection slug from parent directory.
    return src_path.parent.name.lower().replace("_", "-")


def _preview_href(collection_id: str, item_id: str, asset_key: str = "data") -> str:
    """Build a TiTiler preview URL, selecting extreme style when appropriate."""
    style_override = None
    if collection_id == "wrf-daily-rainfall" and "extreme" in item_id.lower():
        style_override = STYLE_PRESETS.get("wrf-extreme-rainfall")
    return build_titiler_preview_href(
        collection_id, item_id, style_override=style_override, asset_key=asset_key
    )


def _run(cmd: list[str], env: Optional[dict[str, str]] = None) -> None:
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )


def _needs_gha_clip(path: Path) -> bool:
    """Return True when raster extends beyond target GHA bbox."""
    try:
        with rasterio.open(path) as ds:
            b = ds.bounds
    except Exception:
        return False
    west, south, east, north = GHA_BBOX
    return b.left < west or b.bottom < south or b.right > east or b.top > north


def _clip_to_gha(src_path: Path) -> Path:
    """Clip raster to GHA admin footprint (dissolved cache with admin0 fallback).

    Uses TemporaryDirectory so temp files are always cleaned up.  The clipped
    result is copied to a sibling of *src_path* before the temp dir is removed.
    """
    db_host = os.getenv("CMS_DB_HOST")
    db_port = os.getenv("CMS_DB_PORT", "5432")
    db_name = os.getenv("CMS_DB_NAME")
    db_user = os.getenv("CMS_DB_USER")
    db_password = os.getenv("CMS_DB_PASSWORD")

    # Stable output location (survives temp-dir cleanup)
    stable_out = src_path.with_name(f"{src_path.stem}_gha_clipped.tif")

    # If DB credentials are unavailable, fallback to strict bbox clip.
    if not all([db_host, db_name, db_user, db_password]):
        with tempfile.TemporaryDirectory(prefix="cog-clip-bbox-") as td_str:
            td = Path(td_str)
            out = td / src_path.name
            west, south, east, north = GHA_BBOX
            _run(
                [
                    "gdalwarp",
                    "-overwrite",
                    "-te",
                    str(west),
                    str(south),
                    str(east),
                    str(north),
                    "-dstnodata",
                    "-32768",
                    str(src_path),
                    str(out),
                ]
            )
            shutil.copy2(str(out), str(stable_out))
        return stable_out

    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    pg_conn = f"PG:host={db_host} port={db_port} dbname={db_name} user={db_user}"

    with tempfile.TemporaryDirectory(prefix="cog-clip-admin-") as td_str:
        td = Path(td_str)
        dissolved = td / "gha_dissolved_admin_cutline.gpkg"
        fallback = td / "gha_admin0_cutline.gpkg"
        clipped = td / src_path.name

        try:
            _run(
                [
                    "ogr2ogr",
                    "-overwrite",
                    "-f",
                    "GPKG",
                    str(dissolved),
                    pg_conn,
                    "-sql",
                    (
                        "WITH src AS ("
                        "  SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(geom),3)) AS geom "
                        "  FROM gha.admin_extent_cache WHERE id = TRUE"
                        "), parts AS ("
                        "  SELECT (ST_Dump(geom)).geom AS geom FROM src"
                        ") "
                        "SELECT row_number() OVER () AS id, ST_Multi(geom) AS geom "
                        "FROM parts WHERE ST_Area(geom) >= 1e-7 AND ST_NPoints(geom) >= 6"
                    ),
                    "-nln",
                    "gha_dissolved_admin_cutline",
                    "-nlt",
                    "MULTIPOLYGON",
                    "-a_srs",
                    "EPSG:4326",
                ],
                env=env,
            )
            _run(
                [
                    "gdalwarp",
                    "-overwrite",
                    "-cutline",
                    str(dissolved),
                    "-cl",
                    "gha_dissolved_admin_cutline",
                    "-crop_to_cutline",
                    "-dstnodata",
                    "-32768",
                    str(src_path),
                    str(clipped),
                ]
            )
        except Exception:
            _run(
                [
                    "ogr2ogr",
                    "-overwrite",
                    "-f",
                    "GPKG",
                    str(fallback),
                    pg_conn,
                    "-sql",
                    (
                        "SELECT row_number() OVER () AS id, "
                        "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom),3)) AS geom "
                        "FROM gha.admin0 WHERE geom IS NOT NULL"
                    ),
                    "-nln",
                    "gha_admin0_cutline",
                    "-nlt",
                    "MULTIPOLYGON",
                    "-a_srs",
                    "EPSG:4326",
                ],
                env=env,
            )
            _run(
                [
                    "gdalwarp",
                    "-overwrite",
                    "-cutline",
                    str(fallback),
                    "-cl",
                    "gha_admin0_cutline",
                    "-crop_to_cutline",
                    "-dstnodata",
                    "-32768",
                    str(src_path),
                    str(clipped),
                ]
            )

        shutil.copy2(str(clipped), str(stable_out))

    return stable_out


def _raster_metadata(path: Path) -> dict:
    with rasterio.open(path) as ds:
        bounds = array_bounds(ds.height, ds.width, ds.transform)
        crs = ds.crs
        meta = {
            "bounds": bounds,
            "crs_epsg": crs.to_epsg() if crs else None,
            "width": ds.width,
            "height": ds.height,
            "dtype": str(ds.dtypes[0]),
            "band_count": ds.count,
            "nodata": ds.nodata,
            "transform": list(ds.transform),
            "file_size": path.stat().st_size,
        }
        if crs and crs.to_epsg() != 4326:
            from rasterio.warp import transform_bounds
            meta["bbox_4326"] = transform_bounds(crs, "EPSG:4326", *bounds)
        else:
            meta["bbox_4326"] = bounds
    return meta


def generate_stac_item(
    cog_path: Path, src_path: Path, collection_id: Optional[str] = None
) -> dict:
    """Create a STAC Item dict for a COG."""
    rmeta = _raster_metadata(cog_path)
    bbox = list(rmeta["bbox_4326"])
    geom = mapping(box(*bbox))
    now = datetime.now(timezone.utc)
    item_id = cog_path.stem
    coll = collection_id or _guess_collection(src_path)

    data_href = public_cog_href(cog_path)
    preview_href = _preview_href(coll, item_id)

    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": item_id,
        "geometry": geom,
        "bbox": bbox,
        "properties": {
            "datetime": now.isoformat(),
            "created": now.isoformat(),
            "proj:epsg": rmeta["crs_epsg"],
            "proj:shape": [rmeta["height"], rmeta["width"]],
            "proj:transform": rmeta["transform"],
        },
        "collection": coll,
        "links": [
            {
                "rel": "preview",
                "href": preview_href,
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
            },
            "thumbnail": {
                "href": preview_href,
                "type": "image/png",
                "title": f"{item_id} thumbnail",
                "roles": ["thumbnail", "overview"],
            },
        },
    }


def write_stac_item(
    cog_path: Path, src_path: Path, collection_id: Optional[str] = None
) -> Path:
    stac_dict = generate_stac_item(cog_path, src_path, collection_id)
    json_path = cog_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(stac_dict, f, indent=2, default=str)
    logger.info("STAC item written: %s", json_path)
    return json_path


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """FloodWatch COG conversion utility."""
    _setup_logging(verbose)


@cli.command()
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--profile", type=click.Choice(list(cog_profiles.keys())), default=COG_PROFILE, show_default=True)
@click.option("--blocksize", type=int, default=COG_BLOCKSIZE, show_default=True)
@click.option("--collection", type=str, default=None)
@click.option("--no-stac", is_flag=True, help="Skip STAC item generation.")
@click.option("--no-validate", is_flag=True, help="Skip COG validation.")
@click.option("--auto-clip/--no-auto-clip", default=True, show_default=True, help="Auto-clip rasters to GHA admin footprint when source extends outside GHA.")
def single(src, output_dir, profile, blocksize, collection, no_stac, no_validate, auto_clip):
    """Convert a single GeoTIFF to COG."""
    dst = _resolve_output_path(src, output_dir)
    logger.info("Converting %s -> %s", src, dst)
    source_for_cog = src
    if auto_clip and _needs_gha_clip(src):
        logger.info("Source outside GHA extent; clipping before COG conversion: %s", src)
        source_for_cog = _clip_to_gha(src)
    convert_to_cog(source_for_cog, dst, profile_name=profile, blocksize=blocksize)

    if not no_validate:
        ok = validate_cog(dst)
        if not ok:
            click.echo(click.style(f"INVALID COG: {dst}", fg="red"))
            sys.exit(1)
        click.echo(click.style(f"VALID COG: {dst}", fg="green"))

    if not no_stac:
        write_stac_item(dst, src, collection_id=collection)


@cli.command()
@click.argument("src_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(file_okay=False, path_type=Path), default=str(DEFAULT_OUTPUT_ROOT), show_default=True)
@click.option("--profile", type=click.Choice(list(cog_profiles.keys())), default=COG_PROFILE, show_default=True)
@click.option("--blocksize", type=int, default=COG_BLOCKSIZE, show_default=True)
@click.option("--collection", type=str, default=None)
@click.option("--no-stac", is_flag=True)
@click.option("--no-validate", is_flag=True)
@click.option("--pattern", type=str, default="*.tif", show_default=True)
@click.option("--auto-clip/--no-auto-clip", default=True, show_default=True, help="Auto-clip rasters to GHA admin footprint when source extends outside GHA.")
def batch(src_dir, output_dir, profile, blocksize, collection, no_stac, no_validate, pattern, auto_clip):
    """Batch-convert all matching GeoTIFFs under SRC_DIR."""
    output_dir = Path(output_dir)
    sources = sorted(src_dir.rglob(pattern))
    sources = [s for s in sources if not s.stem.endswith("_cog")]

    if not sources:
        click.echo(f"No files matching '{pattern}' found under {src_dir}")
        return

    click.echo(f"Found {len(sources)} file(s) to convert.")
    succeeded = failed = 0

    for i, src in enumerate(sources, 1):
        rel = src.relative_to(src_dir)
        dst = output_dir / rel
        logger.info("Converting [%d/%d] %s", i, len(sources), src)
        try:
            source_for_cog = src
            if auto_clip and _needs_gha_clip(src):
                logger.info("Clipping source to GHA before conversion: %s", src)
                source_for_cog = _clip_to_gha(src)
            convert_to_cog(source_for_cog, dst, profile_name=profile, blocksize=blocksize)
            if not no_validate and not validate_cog(dst):
                failed += 1
                continue
            if not no_stac:
                write_stac_item(dst, src, collection_id=collection)
            succeeded += 1
            click.echo(click.style(f"  OK: {dst}", fg="green"))
        except Exception:
            logger.exception("Failed to convert %s", src)
            failed += 1

    click.echo(f"\nDone. Succeeded: {succeeded}  Failed: {failed}")
    if failed:
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def validate(path):
    """Validate that a file is a Cloud Optimized GeoTIFF."""
    ok = validate_cog(path)
    if ok:
        click.echo(click.style(f"VALID COG: {path}", fg="green"))
    else:
        click.echo(click.style(f"INVALID COG: {path}", fg="red"))
        sys.exit(1)


if __name__ == "__main__":
    cli()
