#!/usr/bin/env python3
"""
Download Google Flood Inundation History tiles for Greater Horn of Africa.

This script downloads GeoJSON tiles from Google's public GCS bucket and saves
them locally. Can be run standalone without database connection.

Usage:
    python download_inundation_tiles.py [--output-dir /path/to/output]
    python download_inundation_tiles.py --merge  # Merge all tiles into one file

Data Source: gs://flood-forecasting/inundation_history/
License: CC-BY-4.0
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# GCS configuration
GCS_BUCKET = "flood-forecasting"
GCS_PREFIX = "inundation_history/data/"
GCS_API_URL = f"https://storage.googleapis.com/storage/v1/b/{GCS_BUCKET}/o"
GCS_DOWNLOAD_URL = f"https://storage.googleapis.com/{GCS_BUCKET}"

# Greater Horn of Africa bounding box
GHOA_BOUNDS = {
    "min_lat": -8,
    "max_lat": 23,
    "min_lon": 19,
    "max_lon": 53
}


def list_ghoa_tiles():
    """List all GeoJSON tiles that overlap with GHoA region."""
    tiles = []
    page_token = None

    print("Fetching tile list from GCS...")

    while True:
        params = {"prefix": GCS_PREFIX, "maxResults": 1000}
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(GCS_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        for item in data.get("items", []):
            name = item["name"]
            if not name.endswith(".geojson"):
                continue

            try:
                parts = name.replace(GCS_PREFIX + "inundation_history_", "").replace(".geojson", "").split("_")
                if len(parts) == 4:
                    tile_lat_min, tile_lon_min, tile_lat_max, tile_lon_max = map(float, parts)

                    if (tile_lat_max >= GHOA_BOUNDS["min_lat"] and
                        tile_lat_min <= GHOA_BOUNDS["max_lat"] and
                        tile_lon_max >= GHOA_BOUNDS["min_lon"] and
                        tile_lon_min <= GHOA_BOUNDS["max_lon"]):

                        tiles.append({
                            "name": name,
                            "filename": name.split("/")[-1],
                            "size_bytes": int(item["size"]),
                            "url": f"{GCS_DOWNLOAD_URL}/{name}"
                        })
            except (ValueError, IndexError):
                continue

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return tiles


def download_tile(tile_info, output_dir):
    """Download a single tile to output directory."""
    output_path = output_dir / tile_info["filename"]

    if output_path.exists():
        return (tile_info["filename"], "skipped", output_path.stat().st_size)

    try:
        response = requests.get(tile_info["url"], timeout=60)
        response.raise_for_status()

        output_path.write_bytes(response.content)
        return (tile_info["filename"], "downloaded", len(response.content))
    except Exception as e:
        return (tile_info["filename"], "failed", str(e))


def merge_tiles(input_dir, output_file):
    """Merge all downloaded tiles into a single GeoJSON file."""
    print(f"Merging tiles from {input_dir}...")

    merged = {
        "type": "FeatureCollection",
        "name": "inundation_history_ghoa",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": []
    }

    geojson_files = list(input_dir.glob("*.geojson"))

    for i, filepath in enumerate(geojson_files, 1):
        print(f"  Processing {filepath.name} ({i}/{len(geojson_files)})")
        try:
            with open(filepath) as f:
                data = json.load(f)

            for feature in data.get("features", []):
                # Add source tile info to properties
                if "properties" not in feature:
                    feature["properties"] = {}
                feature["properties"]["source_tile"] = filepath.name
                merged["features"].append(feature)
        except Exception as e:
            print(f"    Error: {e}")

    print(f"Writing merged file with {len(merged['features'])} features...")
    with open(output_file, 'w') as f:
        json.dump(merged, f)

    print(f"Done! Merged file: {output_file}")
    return len(merged["features"])


def main():
    parser = argparse.ArgumentParser(description="Download Google Flood Inundation History tiles")
    parser.add_argument("--output-dir", "-o", type=Path,
                        default=Path("./inundation_history_tiles"),
                        help="Output directory for downloaded tiles")
    parser.add_argument("--merge", "-m", action="store_true",
                        help="Merge all tiles into a single GeoJSON file")
    parser.add_argument("--merge-output", type=Path,
                        default=Path("./inundation_history_ghoa_merged.geojson"),
                        help="Output path for merged GeoJSON")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="Number of parallel download workers")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force re-download of existing files")

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # List tiles
    tiles = list_ghoa_tiles()
    total_size_mb = sum(t["size_bytes"] for t in tiles) / (1024 * 1024)

    print(f"\nFound {len(tiles)} tiles covering Greater Horn of Africa")
    print(f"Total size: {total_size_mb:.2f} MB")
    print(f"Output directory: {args.output_dir}\n")

    # Download tiles
    stats = {"downloaded": 0, "skipped": 0, "failed": 0}

    if args.force:
        # Delete existing files if force flag is set
        for f in args.output_dir.glob("*.geojson"):
            f.unlink()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_tile, t, args.output_dir): t for t in tiles}

        for i, future in enumerate(as_completed(futures), 1):
            filename, status, info = future.result()
            stats[status] = stats.get(status, 0) + 1

            if status == "downloaded":
                print(f"[{i}/{len(tiles)}] Downloaded: {filename} ({info / 1024:.1f} KB)")
            elif status == "skipped":
                print(f"[{i}/{len(tiles)}] Skipped (exists): {filename}")
            else:
                print(f"[{i}/{len(tiles)}] FAILED: {filename} - {info}")

    print(f"\nDownload complete!")
    print(f"  Downloaded: {stats.get('downloaded', 0)}")
    print(f"  Skipped: {stats.get('skipped', 0)}")
    print(f"  Failed: {stats.get('failed', 0)}")

    # Optionally merge tiles
    if args.merge:
        print("\n" + "=" * 60)
        feature_count = merge_tiles(args.output_dir, args.merge_output)
        print(f"Merged {feature_count} features into {args.merge_output}")


if __name__ == "__main__":
    main()
