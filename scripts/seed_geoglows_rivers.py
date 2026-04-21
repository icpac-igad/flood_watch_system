#!/usr/bin/env python3
"""Seed gha.geoglows_rivers — standalone script, run from project root.

Clips 26 VPU stream files to GHA extent, fetches return-period thresholds
from the public GEOGloWS S3 zarr, and loads the result into the local DB.

Usage:
    # Dry-run (no DB writes, just print summary):
    python3 scripts/seed_geoglows_rivers.py --dry-run

    # Full run (creates table + loads data):
    python3 scripts/seed_geoglows_rivers.py

    # Custom input dirs:
    python3 scripts/seed_geoglows_rivers.py --input-dirs /path/to/gpkgs

    # Custom DB (defaults match local eafw-pgdb on port 5431):
    python3 scripts/seed_geoglows_rivers.py --db-host 127.0.0.1 --db-port 5431

Requirements:
    pip install geopandas pyogrio psycopg2-binary xarray zarr s3fs shapely
"""
from __future__ import annotations

import argparse
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import psycopg2
import pyogrio
from psycopg2.extras import execute_values
from shapely import wkb
from shapely.geometry.base import BaseGeometry

RETURN_PERIODS = (2, 5, 10, 25, 50, 100)
RETRO_ZARR_URI = "s3://geoglows-v2/retrospective/return-periods.zarr"

DEFAULT_INPUT_DIRS = [
    Path("backups/geoglows"),
    Path("backups/geoglows/vpu_downloads"),
]

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
CREATE INDEX geoglows_rivers_geom_idx ON gha.geoglows_rivers USING GIST (geometry);
CREATE INDEX geoglows_rivers_order_idx ON gha.geoglows_rivers (river_order);
"""


def log(msg, *args):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}" % args if args else f"[{ts}] {msg}", flush=True)


@contextmanager
def db_conn(host, port, dbname, user, password):
    conn = psycopg2.connect(host=host, port=port, database=dbname, user=user, password=password)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def find_gpkg_files(input_dirs):
    seen = {}
    for d in input_dirs:
        if not d.is_dir():
            log("WARNING: dir not found, skipping: %s", d)
            continue
        for p in sorted(d.glob("streams_*.gpkg")):
            seen.setdefault(p.name, p)
    return list(seen.values())


def load_gha_extent(conn):
    with conn.cursor() as c:
        c.execute("SELECT ST_AsEWKB(ST_Union(geom)) FROM gha.gha_extent")
        row = c.fetchone()
    if not row or not row[0]:
        raise RuntimeError("gha.gha_extent is empty")
    geom = wkb.loads(bytes(row[0]))
    return geom.buffer(0) if not geom.is_valid else geom


def vpu_overlaps_extent(path, extent_3857_bounds):
    """Fast bbox-only check: does this VPU file overlap the GHA extent at all?"""
    try:
        info = pyogrio.read_info(path)
        fb = info.get("total_bounds") or info.get("bounds")
        if fb is None:
            return True  # can't tell, assume yes
        # Check bbox overlap
        fminx, fminy, fmaxx, fmaxy = fb
        eminx, eminy, emaxx, emaxy = extent_3857_bounds
        return not (fmaxx < eminx or fminx > emaxx or fmaxy < eminy or fminy > emaxy)
    except Exception:
        return True  # on error, don't skip


def read_vpu_rivers(path, extent_4326, extent_3857):
    t0 = time.time()

    # Quick bbox pre-check — skip files that can't possibly overlap GHA
    if not vpu_overlaps_extent(path, extent_3857.bounds):
        log("  %-25s SKIPPED (no bbox overlap, %.1fs)", path.name, time.time() - t0)
        return gpd.GeoDataFrame()

    gdf = pyogrio.read_dataframe(
        path,
        columns=["LINKNO", "strmOrder", "VPUCode"],
        bbox=extent_3857.bounds,
        use_arrow=True,
    )
    if gdf.empty:
        log("  %-25s %7d rivers (%.1fs)", path.name, 0, time.time() - t0)
        return gdf
    gdf = gdf.to_crs("EPSG:4326")
    gdf = gdf[gdf.geometry.intersects(extent_4326)].copy()
    log("  %-25s %7d rivers (%.1fs)", path.name, len(gdf), time.time() - t0)
    return gdf


def load_return_periods(river_ids):
    import xarray as xr

    t0 = time.time()
    log("Opening retrospective zarr (S3, anonymous)...")
    ds = xr.open_zarr(RETRO_ZARR_URI, storage_options={"anon": True})

    river_ids = np.asarray(river_ids, dtype=np.int64)
    available = set(int(v) for v in ds["river_id"].values)
    wanted = [int(r) for r in river_ids if int(r) in available]
    missing = len(river_ids) - len(wanted)
    if missing:
        log("  WARNING: %d of %d river_ids not in zarr (will have NULL rp)", missing, len(river_ids))
    log("  Slicing %d river_ids from zarr...", len(wanted))
    subset = ds["gumbel"].sel(river_id=wanted).load()
    log("  Loaded gumbel: shape=%s (%.1fs)", subset.shape, time.time() - t0)

    rp_index = {int(v): i for i, v in enumerate(ds["return_period"].values)}
    df = pd.DataFrame({"river_id": wanted})
    for rp in RETURN_PERIODS:
        df[f"rp{rp}"] = subset.values[rp_index[rp]].astype(np.float32)
    return df


def build_dataframe(gpkg_paths, extent_4326):
    extent_3857 = gpd.GeoSeries([extent_4326], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]

    log("Clipping %d VPU files to GHA extent...", len(gpkg_paths))
    frames = []
    for p in gpkg_paths:
        gdf = read_vpu_rivers(p, extent_4326, extent_3857)
        if not gdf.empty:
            frames.append(gdf)
    if not frames:
        raise RuntimeError("No rivers found after GHA clip")

    combined = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
    before = len(combined)
    combined = combined.drop_duplicates(subset=["LINKNO"], keep="first")
    log("Combined: %d rivers (%d duplicates removed)", len(combined), before - len(combined))

    multi = combined.geometry.geom_type == "MultiLineString"
    if multi.any():
        log("  %d MultiLineStrings → extracting longest part", multi.sum())
        combined.loc[multi, "geometry"] = combined.loc[multi, "geometry"].apply(
            lambda g: max(g.geoms, key=lambda x: x.length)
        )

    rp_df = load_return_periods(combined["LINKNO"].to_numpy())
    combined = combined.merge(rp_df, left_on="LINKNO", right_on="river_id", how="left")

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


def write_to_db(gdf, conn):
    with conn.cursor() as c:
        log("Creating gha.geoglows_rivers (drops existing)...")
        c.execute(CREATE_TABLE_SQL)

        log("Inserting %d rows...", len(gdf))
        rows = [
            (
                int(r.river_id), int(r.river_order), int(r.vpu_code),
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

        t0 = time.time()
        execute_values(
            c,
            """INSERT INTO gha.geoglows_rivers
               (river_id, river_order, vpu_code,
                rp2, rp5, rp10, rp25, rp50, rp100, geometry)
               VALUES %s""",
            rows,
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::geometry)",
            page_size=5000,
        )
        log("Inserted %d rows (%.1fs)", len(rows), time.time() - t0)

        c.execute("ANALYZE gha.geoglows_rivers")
        c.execute("SELECT COUNT(*), MIN(river_order), MAX(river_order) FROM gha.geoglows_rivers")
        row = c.fetchone()
        log("Final table: %s rows, river_order %s–%s", row[0], row[1], row[2])


def main():
    parser = argparse.ArgumentParser(description="Seed gha.geoglows_rivers from VPU gpkg files")
    parser.add_argument("--input-dirs", nargs="+", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Build dataframe only, skip DB write")
    parser.add_argument("--db-host", default="127.0.0.1")
    parser.add_argument("--db-port", type=int, default=5431)
    parser.add_argument("--db-name", default="geomanager_web")
    parser.add_argument("--db-user", default="geomanager")
    parser.add_argument("--db-password", default="cZn4yBskecQrvv6n")
    args = parser.parse_args()

    input_dirs = args.input_dirs or DEFAULT_INPUT_DIRS
    gpkg_paths = find_gpkg_files(input_dirs)
    if not gpkg_paths:
        log("ERROR: no streams_*.gpkg files found")
        return 1
    log("Found %d VPU files", len(gpkg_paths))

    with db_conn(args.db_host, args.db_port, args.db_name, args.db_user, args.db_password) as conn:
        extent = load_gha_extent(conn)
        log("GHA extent: %s, bounds=%s", extent.geom_type, tuple(round(v, 2) for v in extent.bounds))

    gdf = build_dataframe(gpkg_paths, extent)
    log("Final: %d rivers, %d columns", len(gdf), len(gdf.columns))

    has_rp = gdf["rp100"].notna().sum()
    no_rp = gdf["rp100"].isna().sum()
    log("Return periods: %d with RP data, %d without", has_rp, no_rp)

    if args.dry_run:
        log("DRY RUN — no DB writes. Sample:")
        print(gdf.head(3).to_string())
        return 0

    with db_conn(args.db_host, args.db_port, args.db_name, args.db_user, args.db_password) as conn:
        write_to_db(gdf, conn)

    log("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
