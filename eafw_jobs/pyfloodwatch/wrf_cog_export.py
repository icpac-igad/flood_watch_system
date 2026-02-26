"""Export WRF rainfall data from PostGIS to Cloud Optimized GeoTIFFs.

Reads vector grid-cell rainfall values from the wrf schema and rasterises
them into COG files suitable for MapServer, STAC catalogues, or direct
download.

Grid specification (from wrf.grid_01dd):
    - 381 rows (lat) x 326 cols (lon), 0.1 degree resolution, EPSG:4326
    - Fishnet origin (bottom-left): lon=21.0, lat=-14.0
    - yrow is 1-indexed from bottom (yrow=1 -> lat=-14.0)
    - xcol is 1-indexed from left  (xcol=1 -> lon=21.0)
    - Raster top-left corner: lon=21.0, lat=24.1
    - Raster bottom-right:    lon=53.6, lat=-14.0

Dependencies: rasterio, numpy, sqlalchemy, psycopg2, pystac
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from sqlalchemy import create_engine, text

from .logger_config import setup_logger

# Shared COG utilities — import path depends on whether eafw_stac is installed
# or reachable on sys.path.  Fall back to inlining the essentials.
try:
    from eafw_stac.scripts.cog_utils import (
        GHA_BBOX,
        STYLE_PRESETS,
        build_titiler_preview_href,
        public_cog_href,
    )
except ImportError:
    # Running outside the container where eafw_stac isn't on PYTHONPATH.
    # Add the repo root so the import can succeed.
    _repo_root = Path(__file__).resolve().parents[2]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    try:
        from eafw_stac.scripts.cog_utils import (
            GHA_BBOX,
            STYLE_PRESETS,
            build_titiler_preview_href,
            public_cog_href,
        )
    except ImportError:
        # Ultimate fallback — inline minimal definitions so the module loads.
        GHA_BBOX = (21.0, -12.0, 52.0, 23.0)
        STYLE_PRESETS = {}
        def public_cog_href(cog_path):
            parts = list(cog_path.as_posix().split("/"))
            if "cogs" in parts:
                rel = "/".join(parts[parts.index("cogs") + 1:])
                return f"/stac-cogs/{rel}"
            return str(cog_path)
        def build_titiler_preview_href(collection_id, item_id, style_override=None, asset_key="data"):
            return ""

logger = setup_logger(__name__, "wrf_cog_export.log")

# ---------------------------------------------------------------------------
# Grid constants — must match wrf.ST_CreateFishnet(381, 326, 0.1, 0.1, 21, -14)
# ---------------------------------------------------------------------------
GRID_ROWS = 381       # number of latitude cells
GRID_COLS = 326       # number of longitude cells
GRID_RES = 0.1        # degrees per cell

# Fishnet origin (bottom-left corner of the bottom-left cell)
GRID_LON_MIN = 21.0
GRID_LAT_MIN = -14.0

# Derived bounds (pixel-edge coordinates)
GRID_LON_MAX = GRID_LON_MIN + GRID_COLS * GRID_RES   # 53.6
GRID_LAT_MAX = GRID_LAT_MIN + GRID_ROWS * GRID_RES   # 24.1

# Affine transform: top-left origin, positive dx, negative dy
GRID_TRANSFORM = rasterio.transform.from_bounds(
    GRID_LON_MIN, GRID_LAT_MIN, GRID_LON_MAX, GRID_LAT_MAX,
    GRID_COLS, GRID_ROWS,
)
GRID_CRS = CRS.from_epsg(4326)

# NoData sentinel
NODATA = -9999.0

def _wrf_preview_href(collection: str, item_id: str, percentile: Optional[str] = None) -> str:
    """Build a TiTiler preview URL for a WRF item."""
    is_extreme = percentile is not None or "extreme" in item_id.lower()
    style_key = "wrf-extreme-rainfall" if is_extreme else "wrf-daily-rainfall"
    style = STYLE_PRESETS.get(style_key)
    return build_titiler_preview_href(collection, item_id, style_override=style)


def _needs_gha_clip(path: Path) -> bool:
    """True when raster exceeds GHA bounds."""
    with rasterio.open(path) as ds:
        b = ds.bounds
    west, south, east, north = GHA_BBOX
    return b.left < west or b.bottom < south or b.right > east or b.top > north


def _clip_cog_to_gha(cog_path: Path) -> Path:
    """Clip COG to GHA admin0 boundaries and rewrite as COG in-place."""
    try:
        if not _needs_gha_clip(cog_path):
            return cog_path
    except Exception as exc:
        logger.warning(f"Could not inspect bounds for clipping ({cog_path}): {exc}")
        return cog_path

    db_host = os.getenv("DB_HOST", "eafw-pgdb")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "geomanager_web")
    db_user = os.getenv("DB_USER", "geomanager")
    db_password = os.getenv("DB_PASSWORD", "")

    if not db_password:
        logger.warning("DB_PASSWORD not set; skipping GHA clip for %s", cog_path)
        return cog_path

    tmp_dir = cog_path.parent / ".tmp_clip"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cutline = tmp_dir / "gha_admin0_cutline.gpkg"
    clipped = tmp_dir / f"{cog_path.stem}.clipped.tif"
    clipped_cog = tmp_dir / f"{cog_path.stem}.clipped.cog.tif"

    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    pg_conn = f"PG:host={db_host} port={db_port} dbname={db_name} user={db_user}"

    try:
        subprocess.run(
            [
                "ogr2ogr",
                "-overwrite",
                "-f",
                "GPKG",
                str(cutline),
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
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

        subprocess.run(
            [
                "gdalwarp",
                "-overwrite",
                "-cutline",
                str(cutline),
                "-cl",
                "gha_admin0_cutline",
                "-crop_to_cutline",
                "-dstnodata",
                str(NODATA),
                "-ot",
                "Float32",
                "-co",
                "TILED=YES",
                "-co",
                "COMPRESS=DEFLATE",
                "-co",
                "PREDICTOR=2",
                str(cog_path),
                str(clipped),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        subprocess.run(
            [
                "gdal_translate",
                "-of",
                "COG",
                "-co",
                "COMPRESS=DEFLATE",
                "-co",
                "BLOCKSIZE=256",
                str(clipped),
                str(clipped_cog),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        clipped_cog.replace(cog_path)
        logger.info("Clipped to GHA admin extent: %s", cog_path)
        return cog_path
    except Exception as exc:
        logger.warning("Failed to clip %s to GHA extent: %s", cog_path, exc)
        return cog_path
    finally:
        for p in (cutline, clipped, clipped_cog):
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------

def _get_engine(db_url: Optional[str] = None):
    """Return a SQLAlchemy engine.

    Uses *db_url* if given, else ``DATABASE_URL`` env var, else builds the
    URL from the individual ``DB_*`` env vars used by the rest of the jobs
    package.
    """
    if db_url:
        url = db_url
    elif os.getenv("DATABASE_URL"):
        url = os.environ["DATABASE_URL"]
    else:
        host = os.getenv("DB_HOST", "eafw-pgdb")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "geomanager_web")
        user = os.getenv("DB_USER", "geomanager")
        pw = os.getenv("DB_PASSWORD", "")
        url = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{name}"
    return create_engine(url)


# ---------------------------------------------------------------------------
# Rasterisation
# ---------------------------------------------------------------------------

def rasterize_wrf_grid(
    rows,
    grid_shape: Tuple[int, int] = (GRID_ROWS, GRID_COLS),
    transform=None,
    crs=None,
    value_column: str = "value",
):
    """Convert query result rows to a numpy raster array.

    Parameters
    ----------
    rows : iterable of dict-like
        Each row must have ``yrow``, ``xcol``, and a value column (default
        ``"value"``).  ``yrow`` and ``xcol`` are 1-indexed as stored in
        ``wrf.grid_01dd``.
    grid_shape : tuple
        ``(n_rows, n_cols)`` of the output array.
    transform : Affine, optional
        Rasterio affine transform (defaults to module-level GRID_TRANSFORM).
    crs : CRS, optional
        Coordinate reference system (defaults to EPSG:4326).
    value_column : str
        Name of the column holding the rainfall value.

    Returns
    -------
    tuple of (numpy.ndarray, Affine, CRS)
        2-D float32 array filled with NODATA where no data exists, plus the
        affine transform and CRS ready for rasterio writing.
    """
    n_rows, n_cols = grid_shape
    arr = np.full((n_rows, n_cols), NODATA, dtype=np.float32)

    count = 0
    for row in rows:
        yrow = row["yrow"]
        xcol = row["xcol"]
        val = row[value_column]
        if val is None:
            continue

        # Map 1-indexed DB coordinates to 0-indexed array position.
        # yrow=1 is the bottom row (lat_min), but in the raster array row 0
        # is the top (lat_max), so we flip vertically.
        arr_row = n_rows - yrow       # yrow 381 -> row 0 (top)
        arr_col = xcol - 1            # xcol 1   -> col 0 (left)

        if 0 <= arr_row < n_rows and 0 <= arr_col < n_cols:
            arr[arr_row, arr_col] = float(val)
            count += 1

    logger.info(f"Rasterised {count} grid cells into {n_rows}x{n_cols} array")
    return arr, transform or GRID_TRANSFORM, crs or GRID_CRS


# ---------------------------------------------------------------------------
# COG writing
# ---------------------------------------------------------------------------

def _write_cog(arr: np.ndarray, transform, crs, out_path: Path):
    """Write a single-band Cloud Optimised GeoTIFF."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": arr.shape[1],
        "height": arr.shape[0],
        "count": 1,
        "crs": crs,
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 2,
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }

    # Write the base GeoTIFF, then add overviews for COG
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
        dst.update_tags(ns="rio_overview", resampling="average")

    # Re-open and copy to COG layout using rasterio copy
    # (ensures internal tiling + overview layout is COG-compliant)
    cog_path = out_path.with_suffix(".cog.tif")
    try:
        from rasterio.shutil import copy as rio_copy

        rio_copy(
            str(out_path),
            str(cog_path),
            driver="GTiff",
            copy_src_overviews=True,
            compress="deflate",
            predictor=2,
            tiled=True,
            blockxsize=256,
            blockysize=256,
        )
        # Replace original with COG version
        cog_path.replace(out_path)
    except Exception as exc:
        logger.warning(f"COG copy step failed ({exc}); keeping base tiled TIFF")
        if cog_path.exists():
            cog_path.unlink()

    logger.info(f"Wrote COG: {out_path} ({out_path.stat().st_size:,} bytes)")
    return out_path


# ---------------------------------------------------------------------------
# STAC Item sidecar
# ---------------------------------------------------------------------------

def _write_stac_item(
    cog_path: Path,
    forecast_date: date,
    *,
    valid_date: Optional[date] = None,
    percentile: Optional[str] = None,
    collection: str = "wrf-daily-rainfall",
):
    """Write a minimal STAC Item JSON sidecar next to the COG.

    Returns the path to the written JSON file.
    """
    try:
        import pystac
        from pystac import Item, Asset, MediaType
        from pystac.extensions.eo import Band
    except ImportError:
        logger.warning("pystac not installed — skipping STAC sidecar")
        return None

    item_id_parts = [
        "wrf",
        "extreme" if percentile else "daily",
        str(forecast_date),
    ]
    if percentile:
        item_id_parts.append(percentile)
    if valid_date:
        item_id_parts.append(str(valid_date))
    item_id = "-".join(item_id_parts)

    dt = datetime.combine(valid_date or forecast_date, datetime.min.time())

    with rasterio.open(cog_path) as ds:
        b = ds.bounds
    bbox = [float(b.left), float(b.bottom), float(b.right), float(b.top)]
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

    properties = {
        "wrf:forecast_date": str(forecast_date),
        "wrf:source": "WRF-EAF",
        "wrf:grid_resolution": "0.1deg",
    }
    if percentile:
        properties["wrf:percentile"] = percentile
    if valid_date:
        properties["wrf:valid_date"] = str(valid_date)

    item = Item(
        id=item_id,
        geometry=geometry,
        bbox=bbox,
        datetime=dt,
        properties=properties,
    )
    item.add_asset(
        "data",
        Asset(
            href=public_cog_href(cog_path),
            media_type=MediaType.COG,
            roles=["data"],
            title="Rainfall (mm)",
        ),
    )

    # Add styled preview through TiTiler so STAC browser shows rendered thumbnails.
    preview_href = _wrf_preview_href(collection, item_id, percentile=percentile)
    item.add_asset(
        "thumbnail",
        Asset(
            href=preview_href,
            media_type=MediaType.PNG,
            roles=["thumbnail", "overview"],
            title="Styled rainfall preview",
        ),
    )

    json_path = cog_path.with_suffix(".json")
    item_dict = item.to_dict()
    item_dict["collection"] = collection
    json_path.write_text(json.dumps(item_dict, indent=2, default=str))
    logger.info(f"Wrote STAC item: {json_path}")
    return json_path


# ---------------------------------------------------------------------------
# Public API — extreme rainfall
# ---------------------------------------------------------------------------

def export_extreme_rainfall_cog(
    db_url: Optional[str],
    forecast_date: Union[str, date],
    output_dir: Union[str, Path],
    percentile: str = "f95",
) -> Path:
    """Export extreme rainfall for one percentile as a COG.

    Parameters
    ----------
    db_url : str or None
        SQLAlchemy database URL. Falls back to env vars if None.
    forecast_date : str or date
        Forecast issue date (YYYY-MM-DD or date object).
    output_dir : str or Path
        Root output directory.
    percentile : str
        One of ``f90``, ``f95``, ``f99``.

    Returns
    -------
    Path
        Absolute path to the written COG file.
    """
    if isinstance(forecast_date, str):
        forecast_date = date.fromisoformat(forecast_date)
    if percentile not in ("f90", "f95", "f99"):
        raise ValueError(f"Invalid percentile: {percentile!r} (expected f90/f95/f99)")

    output_dir = Path(output_dir)
    engine = _get_engine(db_url)

    col = f"{percentile}_mm"
    query = text("""
        SELECT g.yrow, g.xcol, e.:col AS value
        FROM wrf.grid_01dd g
        JOIN wrf.extreme_rainfall e ON g.id = e.grid_id
        WHERE e.forecast_date = :fdate
          AND e.:col > 0
    """.replace(":col", col))
    # We replaced :col textually because column names cannot be SQL-bound params.

    logger.info(
        f"Querying extreme rainfall: forecast_date={forecast_date}, "
        f"percentile={percentile}"
    )
    with engine.connect() as conn:
        result = conn.execute(query, {"fdate": forecast_date})
        rows = [dict(r._mapping) for r in result]

    logger.info(f"Fetched {len(rows)} non-zero grid cells")
    if not rows:
        logger.warning("No data — writing empty (NODATA) raster")

    arr, transform, crs = rasterize_wrf_grid(rows)

    cog_path = (
        output_dir
        / "wrf-extreme-rainfall"
        / str(forecast_date)
        / f"wrf_extreme_{percentile}.tif"
    )
    _write_cog(arr, transform, crs, cog_path)
    _clip_cog_to_gha(cog_path)
    _write_stac_item(
        cog_path, forecast_date, percentile=percentile, collection="wrf-extreme-rainfall"
    )
    return cog_path


# ---------------------------------------------------------------------------
# Public API — daily rainfall
# ---------------------------------------------------------------------------

def export_daily_rainfall_cog(
    db_url: Optional[str],
    forecast_date: Union[str, date],
    valid_date: Union[str, date],
    output_dir: Union[str, Path],
) -> Path:
    """Export daily rainfall for one valid date as a COG.

    Parameters
    ----------
    db_url : str or None
        SQLAlchemy database URL.
    forecast_date : str or date
        Forecast issue date.
    valid_date : str or date
        Valid (target) date for the rainfall forecast.
    output_dir : str or Path
        Root output directory.

    Returns
    -------
    Path
        Absolute path to the written COG file.
    """
    if isinstance(forecast_date, str):
        forecast_date = date.fromisoformat(forecast_date)
    if isinstance(valid_date, str):
        valid_date = date.fromisoformat(valid_date)

    output_dir = Path(output_dir)
    engine = _get_engine(db_url)

    query = text("""
        SELECT g.yrow, g.xcol, d.rainfall_mm AS value
        FROM wrf.grid_01dd g
        JOIN wrf.daily_rainfall d ON g.id = d.grid_id
        WHERE d.forecast_date = :fdate
          AND d.valid_date = :vdate
          AND d.rainfall_mm > 0
    """)

    logger.info(
        f"Querying daily rainfall: forecast_date={forecast_date}, "
        f"valid_date={valid_date}"
    )
    with engine.connect() as conn:
        result = conn.execute(query, {"fdate": forecast_date, "vdate": valid_date})
        rows = [dict(r._mapping) for r in result]

    logger.info(f"Fetched {len(rows)} non-zero grid cells")
    if not rows:
        logger.warning("No data — writing empty (NODATA) raster")

    arr, transform, crs = rasterize_wrf_grid(rows)

    cog_path = (
        output_dir
        / "wrf-daily-rainfall"
        / str(forecast_date)
        / f"wrf_daily_{valid_date}.tif"
    )
    _write_cog(arr, transform, crs, cog_path)
    _clip_cog_to_gha(cog_path)
    _write_stac_item(
        cog_path,
        forecast_date,
        valid_date=valid_date,
        collection="wrf-daily-rainfall",
    )
    return cog_path


# ---------------------------------------------------------------------------
# Public API — batch export for a forecast date
# ---------------------------------------------------------------------------

def export_all_for_forecast(
    db_url: Optional[str],
    forecast_date: Union[str, date],
    output_dir: Union[str, Path],
    stac_api_url: Optional[str] = None,
) -> List[Path]:
    """Export all extreme percentiles and daily valid dates for a forecast.

    Parameters
    ----------
    db_url : str or None
        SQLAlchemy database URL.
    forecast_date : str or date
        Forecast issue date.
    output_dir : str or Path
        Root output directory.
    stac_api_url : str, optional
        If provided, register each item against this STAC Transaction API.

    Returns
    -------
    list of Path
        Paths to all written COG files.
    """
    if isinstance(forecast_date, str):
        forecast_date = date.fromisoformat(forecast_date)

    output_dir = Path(output_dir)
    engine = _get_engine(db_url)
    cogs: List[Path] = []

    # --- Extreme rainfall (3 percentiles) ---------------------------------
    for pct in ("f90", "f95", "f99"):
        logger.info(f"Exporting extreme rainfall {pct} for {forecast_date}")
        try:
            path = export_extreme_rainfall_cog(db_url, forecast_date, output_dir, pct)
            cogs.append(path)
        except Exception as exc:
            logger.error(f"Failed to export extreme {pct}: {exc}")

    # --- Daily rainfall (all valid dates for this forecast) ----------------
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT DISTINCT valid_date
                FROM wrf.daily_rainfall
                WHERE forecast_date = :fdate
                ORDER BY valid_date
            """),
            {"fdate": forecast_date},
        )
        valid_dates = [r[0] for r in result]

    logger.info(
        f"Found {len(valid_dates)} valid dates for forecast {forecast_date}"
    )

    for vdate in valid_dates:
        logger.info(f"Exporting daily rainfall for valid_date={vdate}")
        try:
            path = export_daily_rainfall_cog(db_url, forecast_date, vdate, output_dir)
            cogs.append(path)
        except Exception as exc:
            logger.error(f"Failed to export daily {vdate}: {exc}")

    # --- Optional STAC registration ---------------------------------------
    if stac_api_url and cogs:
        _register_stac_items(stac_api_url, cogs)

    logger.info(
        f"Export complete for {forecast_date}: {len(cogs)} COGs written"
    )
    return cogs


def _register_stac_items(stac_api_url: str, cog_paths: List[Path]):
    """POST each STAC Item JSON sidecar to a STAC Transaction API.

    Requires the STAC API to support the Transaction extension (POST items).
    Silently skips items whose sidecar JSON is missing.
    """
    try:
        import requests
    except ImportError:
        logger.warning("requests not installed — skipping STAC registration")
        return

    registered = 0
    for cog_path in cog_paths:
        json_path = cog_path.with_suffix(".json")
        if not json_path.exists():
            continue
        try:
            item_dict = json.loads(json_path.read_text())
            collection_id = item_dict.get("collection", "wrf-daily-rainfall")

            # Normalize only the primary raster data asset href.
            assets = item_dict.get("assets", {})
            data_asset = assets.get("data")
            if data_asset and "href" in data_asset:
                href = str(data_asset["href"])
                if not href.startswith(("http://", "https://", "/stac-cogs/")):
                    data_asset["href"] = public_cog_href(cog_path)

            url = f"{stac_api_url.rstrip('/')}/collections/{collection_id}/items"
            resp = requests.post(url, json=item_dict, timeout=30)
            resp.raise_for_status()
            registered += 1
            logger.info(f"Registered STAC item: {item_dict['id']}")
        except Exception as exc:
            logger.warning(f"Failed to register {json_path.name}: {exc}")

    logger.info(f"STAC registration: {registered}/{len(cog_paths)} items")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Minimal CLI for manual runs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export WRF rainfall from PostGIS to Cloud Optimised GeoTIFFs"
    )
    parser.add_argument(
        "forecast_date",
        help="Forecast date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=os.getenv("COG_OUTPUT_DIR", "/data/cogs"),
        help="Root output directory (default: /data/cogs or $COG_OUTPUT_DIR)",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="SQLAlchemy DB URL (default: from env vars)",
    )
    parser.add_argument(
        "--stac-api-url",
        default=None,
        help="STAC Transaction API URL for registration",
    )
    parser.add_argument(
        "--only-extreme",
        action="store_true",
        help="Export only extreme rainfall percentiles",
    )
    parser.add_argument(
        "--only-daily",
        action="store_true",
        help="Export only daily rainfall COGs",
    )
    parser.add_argument(
        "--percentile",
        choices=["f90", "f95", "f99"],
        help="Export a single percentile (implies --only-extreme)",
    )
    parser.add_argument(
        "--valid-date",
        help="Export a single valid date (implies --only-daily, YYYY-MM-DD)",
    )

    args = parser.parse_args()
    fdate = date.fromisoformat(args.forecast_date)
    output_dir = Path(args.output_dir)

    if args.percentile:
        path = export_extreme_rainfall_cog(
            args.db_url, fdate, output_dir, args.percentile
        )
        print(f"Wrote: {path}")
    elif args.valid_date:
        vdate = date.fromisoformat(args.valid_date)
        path = export_daily_rainfall_cog(
            args.db_url, fdate, vdate, output_dir
        )
        print(f"Wrote: {path}")
    elif args.only_extreme:
        for pct in ("f90", "f95", "f99"):
            path = export_extreme_rainfall_cog(
                args.db_url, fdate, output_dir, pct
            )
            print(f"Wrote: {path}")
    elif args.only_daily:
        engine = _get_engine(args.db_url)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT DISTINCT valid_date
                    FROM wrf.daily_rainfall
                    WHERE forecast_date = :fdate
                    ORDER BY valid_date
                """),
                {"fdate": fdate},
            )
            for (vdate,) in result:
                path = export_daily_rainfall_cog(
                    args.db_url, fdate, vdate, output_dir
                )
                print(f"Wrote: {path}")
    else:
        cogs = export_all_for_forecast(
            args.db_url, fdate, output_dir, stac_api_url=args.stac_api_url
        )
        for p in cogs:
            print(f"Wrote: {p}")


if __name__ == "__main__":
    main()
