"""Initial seed for gha.geoglows_rivers.

Reads every ``streams_{vpu}.gpkg`` file found under the repository's
``backups/geoglows`` tree, clips each to the authoritative ``gha.gha_extent``
polygon, pulls return-period thresholds from the public GEOGloWS retrospective
zarr on S3, and writes the result into a new ``gha.geoglows_rivers`` table
that matches the schema expected by the ``gha.geoglows_forecast_rivers`` tile
function.

The script is idempotent. Running it again drops and re-creates the table from
scratch so it can be re-run after any input gpkg or filter change.

Usage (run from the repo root, against a database reachable via ``DB_CONFIG``)::

    python -m eafw_jobs.pyfloodwatch.geoglows_seed                 # full run
    python -m eafw_jobs.pyfloodwatch.geoglows_seed --dry-run       # build df, skip DB writes
    python -m eafw_jobs.pyfloodwatch.geoglows_seed --input-dirs path1 path2

The daily ``geoglows_sync`` job UPDATEs ``alert_level``, ``max_forecast``,
``forecast_date`` and ``updated_at`` on the rows created here — it does not
touch geometry or the rp* columns.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from shapely.geometry.base import BaseGeometry

from .database import get_db_connection
from .logger_config import setup_logger

logger = setup_logger(__name__, "geoglows_seed.log")

# Columns the tile function selects from gha.geoglows_rivers:
#   river_id, river_order, alert_level, max_forecast,
#   rp2, rp5, rp10, rp25, rp50, rp100, geometry
# plus bookkeeping: forecast_date, updated_at.
RETURN_PERIODS = (2, 5, 10, 25, 50, 100)

RETRO_ZARR_URI = "s3://geoglows-v2/retrospective/return-periods.zarr"

DEFAULT_INPUT_DIRS = (
    Path("backups/geoglows"),
    Path("backups/geoglows/vpu_downloads"),
)

CREATE_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS gha;

DROP TABLE IF EXISTS gha.geoglows_rivers CASCADE;

CREATE TABLE gha.geoglows_rivers (
    river_id       bigint PRIMARY KEY,
    river_order    smallint NOT NULL,
    vpu_code       smallint NOT NULL,
    rp2            real,
    rp5            real,
    rp10           real,
    rp25           real,
    rp50           real,
    rp100          real,
    alert_level    smallint NOT NULL DEFAULT 0,
    max_forecast   real,
    forecast_date  timestamptz,
    updated_at     timestamptz NOT NULL DEFAULT NOW(),
    geometry       geometry(LineString, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS geoglows_rivers_geom_idx
    ON gha.geoglows_rivers USING GIST (geometry);

CREATE INDEX IF NOT EXISTS geoglows_rivers_order_idx
    ON gha.geoglows_rivers (river_order);
"""


def find_gpkg_files(input_dirs: Iterable[Path]) -> list[Path]:
    """Return a de-duplicated list of streams_*.gpkg files under the given dirs."""
    seen: dict[str, Path] = {}
    for d in input_dirs:
        if not d.is_dir():
            logger.warning("input dir not found, skipping: %s", d)
            continue
        for p in sorted(d.glob("streams_*.gpkg")):
            # de-dupe by basename so we never load the same VPU twice
            seen.setdefault(p.name, p)
    return list(seen.values())


def load_gha_extent(conn) -> BaseGeometry:
    """Read the dissolved GHA extent polygon from the database."""
    with conn.cursor() as c:
        c.execute("SELECT ST_AsEWKB(ST_Union(geom)) FROM gha.gha_extent")
        row = c.fetchone()
    if not row or not row[0]:
        raise RuntimeError("gha.gha_extent is empty — cannot proceed")
    from shapely import wkb
    geom = wkb.loads(bytes(row[0]))
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom


def read_vpu_rivers(
    path: Path, extent_4326: BaseGeometry, extent_3857: BaseGeometry
) -> gpd.GeoDataFrame:
    """Read one VPU gpkg and return rivers intersecting the GHA extent in EPSG:4326.

    The streams files are stored in EPSG:3857 so we pass pyogrio a 3857 bbox
    (cheap, loose filter) to avoid paging in rivers far outside the region,
    then do the precise polygon intersection in 4326 after reprojection.
    """
    t0 = time.time()
    gdf = pyogrio.read_dataframe(
        path,
        columns=["LINKNO", "strmOrder", "VPUCode"],
        bbox=extent_3857.bounds,
        use_arrow=True,
    )
    if gdf.empty:
        logger.info("%-20s %6d rivers in GHA (%.1fs)", path.name, 0, time.time() - t0)
        return gdf
    gdf = gdf.to_crs("EPSG:4326")
    # Final precise intersection against the real GHA polygon, not its bbox.
    gdf = gdf[gdf.geometry.intersects(extent_4326)].copy()
    logger.info(
        "%-20s %6d rivers in GHA (%.1fs)",
        path.name,
        len(gdf),
        time.time() - t0,
    )
    return gdf


def load_return_periods(river_ids: np.ndarray) -> pd.DataFrame:
    """Slice the retrospective zarr and return rp{2,5,10,25,50,100} per river_id."""
    import xarray as xr

    t0 = time.time()
    logger.info("opening retrospective zarr: %s", RETRO_ZARR_URI)
    ds = xr.open_zarr(RETRO_ZARR_URI, storage_options={"anon": True})
    if set(RETURN_PERIODS) - set(int(v) for v in ds["return_period"].values):
        raise RuntimeError(
            f"retrospective zarr missing one of the expected return periods: "
            f"{RETURN_PERIODS} vs {ds['return_period'].values.tolist()}"
        )

    # Ask the zarr for only the river_ids we need. xarray + dask will fetch
    # just the chunks that cover them — typically tens of MB instead of 550.
    river_ids = np.asarray(river_ids, dtype=np.int64)
    available = set(int(v) for v in ds["river_id"].values)
    wanted = [int(r) for r in river_ids if int(r) in available]
    missing = len(river_ids) - len(wanted)
    if missing:
        logger.warning(
            "%d of %d river_ids not present in retrospective zarr — "
            "those rivers will have NULL return periods",
            missing,
            len(river_ids),
        )
    subset = ds["gumbel"].sel(river_id=wanted).load()
    logger.info(
        "loaded gumbel rp slice: shape=%s (%.1fs)",
        tuple(subset.shape),
        time.time() - t0,
    )

    rp_index = {int(v): i for i, v in enumerate(ds["return_period"].values)}
    df = pd.DataFrame({"river_id": wanted})
    for rp in RETURN_PERIODS:
        df[f"rp{rp}"] = subset.values[rp_index[rp]].astype(np.float32)
    return df


def build_dataframe(gpkg_paths: list[Path], extent_4326: BaseGeometry) -> gpd.GeoDataFrame:
    """Read every VPU, clip to GHA, drop duplicates, join return periods."""
    # Reproject the extent to web mercator once so pyogrio's bbox filter
    # operates in the dataset's native CRS without per-file overhead.
    extent_3857 = (
        gpd.GeoSeries([extent_4326], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
    )

    frames = []
    for p in gpkg_paths:
        gdf = read_vpu_rivers(p, extent_4326, extent_3857)
        if not gdf.empty:
            frames.append(gdf)
    if not frames:
        raise RuntimeError("no rivers found in any input gpkg after GHA clip")

    combined = gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), crs="EPSG:4326"
    )
    before = len(combined)
    combined = combined.drop_duplicates(subset=["LINKNO"], keep="first")
    after = len(combined)
    logger.info("combined: %d rivers (%d duplicates removed)", after, before - after)

    # Only keep geometry as simple LineStrings (drop the occasional
    # MultiLineString with a warning — the tile function expects LineString)
    multi = combined.geometry.geom_type == "MultiLineString"
    if multi.any():
        logger.warning("%d rivers are MultiLineString — exploding to first part", multi.sum())
        combined.loc[multi, "geometry"] = combined.loc[multi, "geometry"].apply(
            lambda g: max(g.geoms, key=lambda x: x.length)
        )

    rp_df = load_return_periods(combined["LINKNO"].to_numpy())
    combined = combined.merge(rp_df, left_on="LINKNO", right_on="river_id", how="left")

    # Final schema the DB expects
    result = gpd.GeoDataFrame(
        {
            "river_id": combined["LINKNO"].astype(np.int64),
            "river_order": combined["strmOrder"].astype(np.int16),
            "vpu_code": combined["VPUCode"].astype(np.int16),
            "rp2": combined["rp2"],
            "rp5": combined["rp5"],
            "rp10": combined["rp10"],
            "rp25": combined["rp25"],
            "rp50": combined["rp50"],
            "rp100": combined["rp100"],
            "geometry": combined.geometry,
        },
        crs="EPSG:4326",
    )
    return result


def write_to_db(gdf: gpd.GeoDataFrame) -> None:
    """Create the table and bulk-load the dataframe."""
    from shapely import wkb

    with get_db_connection() as conn:
        with conn.cursor() as c:
            logger.info("creating gha.geoglows_rivers (drops existing)")
            c.execute(CREATE_TABLE_SQL)

            logger.info("preparing %d rows for insert", len(gdf))
            rows = [
                (
                    int(r.river_id),
                    int(r.river_order),
                    int(r.vpu_code),
                    None if pd.isna(r.rp2) else float(r.rp2),
                    None if pd.isna(r.rp5) else float(r.rp5),
                    None if pd.isna(r.rp10) else float(r.rp10),
                    None if pd.isna(r.rp25) else float(r.rp25),
                    None if pd.isna(r.rp50) else float(r.rp50),
                    None if pd.isna(r.rp100) else float(r.rp100),
                    wkb.dumps(r.geometry, hex=True, srid=4326),
                )
                for r in gdf.itertuples(index=False)
            ]

            from psycopg2.extras import execute_values

            t0 = time.time()
            execute_values(
                c,
                """
                INSERT INTO gha.geoglows_rivers
                    (river_id, river_order, vpu_code,
                     rp2, rp5, rp10, rp25, rp50, rp100, geometry)
                VALUES %s
                """,
                rows,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::geometry)",
                page_size=5000,
            )
            logger.info("inserted %d rows (%.1fs)", len(rows), time.time() - t0)

            c.execute("ANALYZE gha.geoglows_rivers")

            c.execute("SELECT COUNT(*), MIN(river_order), MAX(river_order) FROM gha.geoglows_rivers")
            row = c.fetchone()
            logger.info(
                "final table: count=%s min_order=%s max_order=%s",
                row[0],
                row[1],
                row[2],
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dirs",
        nargs="+",
        type=Path,
        default=None,
        help="Directories containing streams_{vpu}.gpkg files (default: "
        "backups/geoglows and backups/geoglows/vpu_downloads)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the dataframe and print a summary, do not write to DB",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(args.log_level)

    input_dirs = args.input_dirs or list(DEFAULT_INPUT_DIRS)
    gpkg_paths = find_gpkg_files(input_dirs)
    if not gpkg_paths:
        logger.error("no streams_*.gpkg files found under %s", input_dirs)
        return 2
    logger.info("found %d VPU files:", len(gpkg_paths))
    for p in gpkg_paths:
        logger.info("  %s", p)

    with get_db_connection() as conn:
        extent = load_gha_extent(conn)
        logger.info(
            "gha.gha_extent: type=%s bounds=%s",
            extent.geom_type,
            tuple(round(v, 3) for v in extent.bounds),
        )

    gdf = build_dataframe(gpkg_paths, extent)
    logger.info("final dataframe: %d rows, %d columns", len(gdf), len(gdf.columns))
    logger.info("sample: %s", gdf.head(2).to_dict(orient="records"))

    missing_rp = gdf["rp100"].isna().sum()
    if missing_rp:
        logger.warning(
            "%d rivers (%.1f%%) have NULL return periods",
            missing_rp,
            100.0 * missing_rp / len(gdf),
        )

    if args.dry_run:
        logger.info("dry run — skipping database write")
        return 0

    write_to_db(gdf)
    logger.info("seed complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
