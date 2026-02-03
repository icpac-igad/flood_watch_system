#!/usr/bin/env python3
"""
Ingest daily HMC alert raster data into PostGIS grid table.
Converts GeoTIFF raster to grid cell values for MapServer rendering.
"""

import os
import sys
import argparse
from datetime import datetime
import rasterio
import numpy as np
import psycopg2
from psycopg2.extras import execute_values


def parse_date_from_filename(filename):
    """Extract date from filename like 'hmc_alert_daily_20241128.tif'"""
    basename = os.path.basename(filename)
    # Try to extract YYYYMMDD pattern
    import re
    match = re.search(r'(\d{8})', basename)
    if match:
        date_str = match.group(1)
        return datetime.strptime(date_str, '%Y%m%d').date()
    raise ValueError(f"Could not extract date from filename: {filename}")


def get_grid_mapping(conn, resolution=0.1):
    """
    Create mapping of (xcol, yrow) -> grid_id for quick lookups.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, xcol, yrow FROM grids.grid_01dd")
    mapping = {}
    for row in cursor.fetchall():
        grid_id, xcol, yrow = row
        mapping[(xcol, yrow)] = grid_id
    cursor.close()
    return mapping


def lon_lat_to_grid_coords(lon, lat, x_origin=21.0, y_origin=-12.0, cell_size=0.1):
    """Convert lon/lat to grid xcol/yrow coordinates."""
    xcol = int((lon - x_origin) / cell_size) + 1
    yrow = int((lat - y_origin) / cell_size) + 1
    return xcol, yrow


def ingest_tiff(tiff_path, conn, alert_date=None, dry_run=False):
    """
    Read a GeoTIFF and ingest alert values into PostGIS.

    Args:
        tiff_path: Path to the GeoTIFF file
        conn: PostgreSQL connection
        alert_date: Date for the alert data (extracted from filename if None)
        dry_run: If True, don't commit changes
    """
    # Parse date from filename if not provided
    if alert_date is None:
        alert_date = parse_date_from_filename(tiff_path)

    print(f"Processing: {tiff_path}")
    print(f"Alert date: {alert_date}")

    # Get grid mapping
    grid_mapping = get_grid_mapping(conn)
    print(f"Loaded {len(grid_mapping)} grid cells")

    # Read raster
    with rasterio.open(tiff_path) as src:
        data = src.read(1)  # Read first band
        transform = src.transform
        nodata = src.nodata

        print(f"Raster shape: {data.shape}")
        print(f"Raster bounds: {src.bounds}")
        print(f"NoData value: {nodata}")

        # Collect values to insert (use dict to dedupe by grid_id, keeping max alert level)
        grid_alerts = {}

        for row_idx in range(data.shape[0]):
            for col_idx in range(data.shape[1]):
                value = data[row_idx, col_idx]

                # Skip nodata and zero values
                if nodata is not None and value == nodata:
                    continue
                if value == 0 or np.isnan(value):
                    continue

                # Convert pixel coordinate to geographic coordinate
                lon, lat = rasterio.transform.xy(transform, row_idx, col_idx)

                # Convert to grid coordinates
                xcol, yrow = lon_lat_to_grid_coords(lon, lat)

                # Look up grid_id
                grid_key = (xcol, yrow)
                if grid_key in grid_mapping:
                    grid_id = grid_mapping[grid_key]
                    alert_level = int(value)
                    # Keep max alert level for each grid cell
                    if grid_id not in grid_alerts or alert_level > grid_alerts[grid_id]:
                        grid_alerts[grid_id] = alert_level

        # Convert to list of tuples
        values_to_insert = [(grid_id, alert_date, level) for grid_id, level in grid_alerts.items()]
        print(f"Found {len(values_to_insert)} unique grid cells with alert values")

        if dry_run:
            print("DRY RUN - not committing changes")
            return len(values_to_insert)

        if values_to_insert:
            cursor = conn.cursor()

            # Delete existing data for this date
            cursor.execute(
                "DELETE FROM alerts.daily_hmc_alerts WHERE alert_date = %s",
                (alert_date,)
            )
            deleted = cursor.rowcount
            print(f"Deleted {deleted} existing records for {alert_date}")

            # Insert new data
            execute_values(
                cursor,
                """
                INSERT INTO alerts.daily_hmc_alerts (grid_id, alert_date, alert_level)
                VALUES %s
                ON CONFLICT (grid_id, alert_date) DO UPDATE SET alert_level = EXCLUDED.alert_level
                """,
                values_to_insert
            )

            conn.commit()
            print(f"Inserted {len(values_to_insert)} records")
            cursor.close()

        return len(values_to_insert)


def main():
    parser = argparse.ArgumentParser(description='Ingest daily HMC alert TIFF files into PostGIS')
    parser.add_argument('tiff_files', nargs='+', help='Path to TIFF file(s)')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', default='5434', help='Database port')
    parser.add_argument('--dbname', default='eafw', help='Database name')
    parser.add_argument('--user', default='gis', help='Database user')
    parser.add_argument('--password', default='changeme', help='Database password')
    parser.add_argument('--dry-run', action='store_true', help='Do not commit changes')

    args = parser.parse_args()

    # Connect to database
    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.dbname,
        user=args.user,
        password=args.password
    )

    try:
        total_records = 0
        for tiff_path in args.tiff_files:
            if not os.path.exists(tiff_path):
                print(f"Warning: File not found: {tiff_path}")
                continue
            records = ingest_tiff(tiff_path, conn, dry_run=args.dry_run)
            total_records += records

        print(f"\nTotal records processed: {total_records}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
