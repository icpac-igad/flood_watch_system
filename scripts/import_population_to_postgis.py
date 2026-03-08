#!/usr/bin/env python3
"""
Import LandScan population raster into PostGIS raster table.

Reads the LandScan 2024 GeoTIFF, clips to the GHoA bounding box,
tiles into 100x100 chunks, and inserts into gha.population_raster
using WKB raster binary format (native PostGIS, no GDAL dependency).

Usage:
    python scripts/import_population_to_postgis.py

Environment variables (or defaults for local docker setup):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, POPULATION_RASTER
"""

import os
import struct
import sys

try:
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds, Window
    import psycopg2
except ImportError:
    print("Required: pip install rasterio psycopg2-binary numpy")
    sys.exit(1)

# GHoA bounding box (covering ICPAC region)
GHOA_BBOX = {
    "west": 21.0,
    "east": 52.0,
    "south": -12.0,
    "north": 24.0,
}

TILE_SIZE = 100  # pixels per tile chunk

RASTER_PATH = os.environ.get("POPULATION_RASTER", "")
if not RASTER_PATH or not os.path.exists(RASTER_PATH):
    RASTER_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data/mapfiles/data/population/landscan_population_2024.tif",
    )

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "9060"),
    "dbname": os.environ.get("DB_NAME", "geomanager_web"),
    "user": os.environ.get("DB_USER", "geomanager"),
    "password": os.environ.get("DB_PASSWORD", "localdevpassword"),
}


def array_to_wkb_raster_hex(data, ul_x, ul_y, scale_x, scale_y, srid, nodata):
    """
    Encode a 2D int32 numpy array as a WKB Raster hex string.

    WKB Raster format spec:
    https://trac.osgeo.org/postgis/wiki/WKTRaster/RFC/RFC2-V0WKBFormat
    """
    height, width = data.shape
    nBands = 1
    pixtype = 5  # 32BSI (signed int32)
    # Band flags: pixtype in bits 0-3, hasnodata = bit 6 (0x40)
    band_flags = pixtype | 0x40  # has nodata

    # Raster header (little-endian)
    header = struct.pack(
        "<"        # little-endian
        "B"        # endianness: 1 = little-endian
        "H"        # version: 0
        "H"        # nBands
        "d"        # scaleX
        "d"        # scaleY
        "d"        # ipX (upper-left X)
        "d"        # ipY (upper-left Y)
        "d"        # skewX
        "d"        # skewY
        "i"        # srid
        "H"        # width
        "H",       # height
        1,         # endianness
        0,         # version
        nBands,
        scale_x,
        scale_y,
        ul_x,
        ul_y,
        0.0,       # skewX
        0.0,       # skewY
        srid,
        width,
        height,
    )

    # Band header: flags byte + nodata value
    band_header = struct.pack("<B", band_flags)
    nodata_bytes = struct.pack("<i", int(nodata))

    # Pixel data: int32 little-endian, row-major
    pixel_data = data.astype("<i4").tobytes()

    wkb = header + band_header + nodata_bytes + pixel_data
    return wkb.hex()


def main():
    print(f"Reading raster: {RASTER_PATH}")
    if not os.path.exists(RASTER_PATH):
        print(f"ERROR: Raster file not found: {RASTER_PATH}")
        sys.exit(1)

    # Connect to PostGIS
    print(f"Connecting to PostgreSQL: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # Ensure postgis_raster extension
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis_raster SCHEMA public CASCADE;")

    # Recreate raster table
    print("Creating table gha.population_raster...")
    cur.execute("DROP TABLE IF EXISTS gha.population_raster CASCADE;")
    cur.execute("""
        CREATE TABLE gha.population_raster (
            rid SERIAL PRIMARY KEY,
            rast raster NOT NULL
        );
    """)

    with rasterio.open(RASTER_PATH) as src:
        # LandScan uses -32768 as actual nodata (declared nodata is -2147483647)
        nodata = -32768
        pixel_width = src.transform.a    # positive
        pixel_height = src.transform.e   # negative

        print(f"Raster: {src.width}x{src.height}, CRS: {src.crs}, "
              f"pixel: {pixel_width:.6f}x{abs(pixel_height):.6f} deg, "
              f"dtype: {src.dtypes[0]}, NoData: {nodata}")

        # Get the window for GHoA extent
        ghoa_window = from_bounds(
            GHOA_BBOX["west"], GHOA_BBOX["south"],
            GHOA_BBOX["east"], GHOA_BBOX["north"],
            src.transform,
        )
        col_off = int(ghoa_window.col_off)
        row_off = int(ghoa_window.row_off)
        width = int(ghoa_window.width) + 1
        height = int(ghoa_window.height) + 1

        print(f"GHoA window: col_off={col_off}, row_off={row_off}, "
              f"width={width}, height={height}")

        n_cols = (width + TILE_SIZE - 1) // TILE_SIZE
        n_rows = (height + TILE_SIZE - 1) // TILE_SIZE
        total_tiles = n_cols * n_rows
        print(f"Tiling into {n_cols}x{n_rows} = {total_tiles} tiles of {TILE_SIZE}x{TILE_SIZE}")

        inserted = 0
        skipped = 0
        nodata_int = int(nodata)

        conn.autocommit = False

        for tr in range(n_rows):
            for tc in range(n_cols):
                tile_col = col_off + tc * TILE_SIZE
                tile_row = row_off + tr * TILE_SIZE
                tile_w = min(TILE_SIZE, col_off + width - tile_col)
                tile_h = min(TILE_SIZE, row_off + height - tile_row)

                if tile_w <= 0 or tile_h <= 0:
                    continue

                window = Window(tile_col, tile_row, tile_w, tile_h)
                data = src.read(1, window=window)

                # Skip tiles that are entirely nodata or zero
                valid_mask = (data > 0) & (data != nodata_int)
                if not valid_mask.any():
                    skipped += 1
                    continue

                # Upper-left corner of this tile
                ul_x = src.transform.c + tile_col * pixel_width
                ul_y = src.transform.f + tile_row * pixel_height

                # Encode as WKB raster hex
                wkb_hex = array_to_wkb_raster_hex(
                    data, ul_x, ul_y,
                    pixel_width, pixel_height,
                    4326, nodata_int,
                )

                cur.execute(
                    "INSERT INTO gha.population_raster (rast) VALUES (%s::raster);",
                    (wkb_hex,),
                )
                inserted += 1

                if inserted % 100 == 0:
                    conn.commit()
                    print(f"  Inserted {inserted} tiles, skipped {skipped} "
                          f"(tile {tr * n_cols + tc + 1}/{total_tiles})")

        conn.commit()
        print(f"\nInserted {inserted} tiles, skipped {skipped} empty tiles")

    # Add spatial index
    print("Adding raster constraints and spatial index...")
    conn.autocommit = True

    try:
        cur.execute("""
            SELECT AddRasterConstraints('gha', 'population_raster', 'rast',
                'srid', 'scale_x', 'scale_y',
                'num_bands', 'pixel_types', 'nodata_values');
        """)
    except Exception as e:
        print(f"Warning: AddRasterConstraints partially failed: {e}")
        conn.rollback()

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_population_raster_rast_st_convexhull
            ON gha.population_raster USING GIST (ST_ConvexHull(rast));
    """)

    cur.execute("ANALYZE gha.population_raster;")

    # Verify
    cur.execute("""
        SELECT count(*),
               ST_Extent(ST_Envelope(rast)::geometry)
        FROM gha.population_raster;
    """)
    count, extent = cur.fetchone()
    print(f"Done! {count} raster tiles loaded. Extent: {extent}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
