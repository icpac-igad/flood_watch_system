#!/usr/bin/env python3
"""
Prepare source rasters for STAC ingestion.

Current behavior:
- Ensures LandScan population is clipped to GHA admin footprint.
- Uses dissolved admin geometry cache first, then falls back to admin0 parts
  when the dissolved cutline has degenerate geometry that GDAL cannot clip.
- Regenerates LandScan COG and STAC item JSON sidecar.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click
import rasterio

LOGGER = logging.getLogger("prepare_rasters")

DEFAULT_SOURCE = Path(
    os.getenv("LANDSCAN_SOURCE", "/data/rasters/population/landscan_population_2024.tif")
)
DEFAULT_COG_DIR = Path(os.getenv("COG_DATA_DIR", "/data/cogs")) / "population"
DEFAULT_COLLECTION = "landscan-population"


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _run(cmd: list[str], env: Optional[dict[str, str]] = None) -> None:
    """Run a subprocess command and raise with captured output on failure."""
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        output = exc.stdout.strip() if exc.stdout else ""
        raise RuntimeError(
            f"Command failed ({' '.join(cmd)}): {output}"
        ) from exc

    if completed.stdout:
        LOGGER.debug(completed.stdout.strip())


def _is_already_gha_clipped(path: Path) -> bool:
    """Return True when raster bounds already match expected GHA window."""
    with rasterio.open(path) as ds:
        bounds = ds.bounds
        return (
            20.0 <= bounds.left <= 24.0
            and 50.0 <= bounds.right <= 53.5
            and -13.5 <= bounds.bottom <= -9.0
            and 22.0 <= bounds.top <= 24.5
            and ds.width <= 8000
            and ds.height <= 8000
        )


def _pg_conn(db_host: str, db_port: int, db_name: str, db_user: str) -> str:
    return f"PG:host={db_host} port={db_port} dbname={db_name} user={db_user}"


def _export_dissolved_cutline(
    cutline_path: Path,
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
    db_password: str,
) -> tuple[Path, str]:
    """
    Export dissolved admin footprint from gha.admin_extent_cache.

    The query removes tiny degenerate parts that frequently break gdalwarp.
    """
    sql = (
        "WITH src AS ("
        "  SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(geom),3)) AS geom "
        "  FROM gha.admin_extent_cache WHERE id = TRUE"
        "), parts AS ("
        "  SELECT (ST_Dump(geom)).geom AS geom FROM src"
        ") "
        "SELECT row_number() OVER () AS id, ST_Multi(geom) AS geom "
        "FROM parts "
        "WHERE ST_Area(geom) >= 1e-7 AND ST_NPoints(geom) >= 6"
    )
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    _run(
        [
            "ogr2ogr",
            "-overwrite",
            "-f",
            "GPKG",
            str(cutline_path),
            _pg_conn(db_host, db_port, db_name, db_user),
            "-sql",
            sql,
            "-nln",
            "gha_dissolved_admin_cutline",
            "-nlt",
            "MULTIPOLYGON",
            "-a_srs",
            "EPSG:4326",
        ],
        env=env,
    )
    return cutline_path, "gha_dissolved_admin_cutline"


def _export_admin0_cutline(
    cutline_path: Path,
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
    db_password: str,
) -> tuple[Path, str]:
    """Fallback cutline export from gha.admin0 country polygons."""
    sql = (
        "SELECT row_number() OVER () AS id, "
        "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom),3)) AS geom "
        "FROM gha.admin0 WHERE geom IS NOT NULL"
    )
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    _run(
        [
            "ogr2ogr",
            "-overwrite",
            "-f",
            "GPKG",
            str(cutline_path),
            _pg_conn(db_host, db_port, db_name, db_user),
            "-sql",
            sql,
            "-nln",
            "gha_admin0_cutline",
            "-nlt",
            "MULTIPOLYGON",
            "-a_srs",
            "EPSG:4326",
        ],
        env=env,
    )
    return cutline_path, "gha_admin0_cutline"


def _clip_raster(source: Path, target: Path, cutline: Path, layer_name: str) -> None:
    _run(
        [
            "gdalwarp",
            "-overwrite",
            "-cutline",
            str(cutline),
            "-cl",
            layer_name,
            "-crop_to_cutline",
            "-dstnodata",
            "-32768",
            "-ot",
            "Int32",
            "-multi",
            "-wo",
            "NUM_THREADS=ALL_CPUS",
            "-co",
            "TILED=YES",
            "-co",
            "COMPRESS=DEFLATE",
            "-co",
            "PREDICTOR=2",
            "-co",
            "BIGTIFF=IF_SAFER",
            str(source),
            str(target),
        ]
    )


@click.command()
@click.option(
    "--source",
    "source_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=DEFAULT_SOURCE,
    show_default=True,
    help="LandScan source raster path.",
)
@click.option(
    "--cog-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=DEFAULT_COG_DIR,
    show_default=True,
    help="Target directory for generated COG and STAC item sidecar.",
)
@click.option("--db-host", default=lambda: os.getenv("CMS_DB_HOST", "eafw_db"), show_default=True)
@click.option("--db-port", default=lambda: int(os.getenv("CMS_DB_PORT", "5432")), show_default=True)
@click.option(
    "--db-name",
    default=lambda: os.getenv("CMS_DB_NAME", "geomanager_web"),
    show_default=True,
)
@click.option(
    "--db-user",
    default=lambda: os.getenv("CMS_DB_USER", "geomanager"),
    show_default=True,
)
@click.option(
    "--db-password",
    default=lambda: os.getenv("CMS_DB_PASSWORD", ""),
    show_default=False,
)
@click.option("--collection", default=DEFAULT_COLLECTION, show_default=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def main(
    source_path: Path,
    cog_dir: Path,
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
    db_password: str,
    collection: str,
    verbose: bool,
) -> None:
    _configure_logging(verbose)
    cog_dir.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        raise click.ClickException(f"LandScan source raster not found: {source_path}")

    clip_input = source_path
    if _is_already_gha_clipped(source_path):
        LOGGER.info("LandScan source already clipped to GHA admin footprint: %s", source_path)
    else:
        if not db_password:
            raise click.ClickException(
                "CMS_DB_PASSWORD is required to export dissolved admin cutline from PostGIS."
            )

        LOGGER.info("Source appears global; clipping to dissolved GHA admin footprint.")
        with tempfile.TemporaryDirectory(prefix="landscan-clip-") as td:
            tmp = Path(td)
            dissolved_cutline = tmp / "gha_dissolved_admin_cutline.gpkg"
            fallback_cutline = tmp / "gha_admin0_cutline.gpkg"
            clipped_tif = tmp / "landscan_population_2024.tif"

            try:
                cutline_path, layer_name = _export_dissolved_cutline(
                    dissolved_cutline,
                    db_host=db_host,
                    db_port=db_port,
                    db_name=db_name,
                    db_user=db_user,
                    db_password=db_password,
                )
                _clip_raster(source_path, clipped_tif, cutline_path, layer_name)
                clip_input = clipped_tif
                LOGGER.info("Clipped using dissolved admin footprint cache.")
            except Exception as exc:
                LOGGER.warning(
                    "Dissolved cutline failed (%s). Falling back to admin0-part cutline.",
                    exc,
                )
                cutline_path, layer_name = _export_admin0_cutline(
                    fallback_cutline,
                    db_host=db_host,
                    db_port=db_port,
                    db_name=db_name,
                    db_user=db_user,
                    db_password=db_password,
                )
                _clip_raster(source_path, clipped_tif, cutline_path, layer_name)
                clip_input = clipped_tif
                LOGGER.info("Clipped using admin0 fallback cutline.")

            cog_script = Path(__file__).with_name("cog_convert.py")
            _run(
                [
                    sys.executable,
                    str(cog_script),
                    "single",
                    str(clip_input),
                    "--output-dir",
                    str(cog_dir),
                    "--collection",
                    collection,
                ]
            )
            LOGGER.info("LandScan COG + STAC item regenerated in: %s", cog_dir)
            return

    cog_script = Path(__file__).with_name("cog_convert.py")
    _run(
        [
            sys.executable,
            str(cog_script),
            "single",
            str(clip_input),
            "--output-dir",
            str(cog_dir),
            "--collection",
            collection,
        ]
    )
    LOGGER.info("LandScan COG + STAC item regenerated in: %s", cog_dir)


if __name__ == "__main__":
    main()
