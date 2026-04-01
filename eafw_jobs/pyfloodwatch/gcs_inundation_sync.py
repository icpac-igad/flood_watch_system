"""
Google Cloud Storage Flood Inundation History Sync

Downloads and ingests historical flood inundation data from Google's
flood-forecasting GCS bucket for the Greater Horn of Africa region.

Data source: gs://flood-forecasting/inundation_history/
License: CC-BY-4.0
"""

import os
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from .database import get_db_connection
from .logger_config import setup_logger
from psycopg2.extras import Json

logger = setup_logger(__name__, 'gcs_inundation.log')

# GCS public bucket configuration
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
    """
    List all GeoJSON tiles from GCS that overlap with GHoA region.

    Returns:
        list: List of tile metadata dicts with 'name', 'size', 'bounds'
    """
    tiles = []
    page_token = None

    while True:
        params = {
            "prefix": GCS_PREFIX,
            "maxResults": 1000
        }
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(GCS_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        for item in data.get("items", []):
            name = item["name"]
            if not name.endswith(".geojson"):
                continue

            # Parse tile bounds from filename
            # Format: inundation_history/data/inundation_history_{lat_min}_{lon_min}_{lat_max}_{lon_max}.geojson
            try:
                parts = name.replace(GCS_PREFIX + "inundation_history_", "").replace(".geojson", "").split("_")
                if len(parts) == 4:
                    tile_lat_min, tile_lon_min, tile_lat_max, tile_lon_max = map(float, parts)

                    # Check if tile overlaps with GHoA region
                    if (tile_lat_max >= GHOA_BOUNDS["min_lat"] and
                        tile_lat_min <= GHOA_BOUNDS["max_lat"] and
                        tile_lon_max >= GHOA_BOUNDS["min_lon"] and
                        tile_lon_min <= GHOA_BOUNDS["max_lon"]):

                        tiles.append({
                            "name": name,
                            "filename": name.split("/")[-1],
                            "size_bytes": int(item["size"]),
                            "bounds": {
                                "min_lat": tile_lat_min,
                                "min_lon": tile_lon_min,
                                "max_lat": tile_lat_max,
                                "max_lon": tile_lon_max
                            }
                        })
            except (ValueError, IndexError):
                continue

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"Found {len(tiles)} tiles covering Greater Horn of Africa")
    return tiles


def download_tile(tile_info):
    """
    Download a single GeoJSON tile from GCS.

    Args:
        tile_info: Dict with 'name' and 'bounds'

    Returns:
        tuple: (tile_info, geojson_data) or (tile_info, None) on error
    """
    url = f"{GCS_DOWNLOAD_URL}/{tile_info['name']}"
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        geojson = response.json()
        return (tile_info, geojson)
    except Exception as e:
        logger.error(f"Failed to download {tile_info['filename']}: {e}")
        return (tile_info, None)


def ingest_inundation_tile(tile_info, geojson_data):
    """
    Ingest a single tile's GeoJSON data into the database.

    The database function will handle clipping to admin boundaries.

    Args:
        tile_info: Tile metadata dict
        geojson_data: GeoJSON FeatureCollection

    Returns:
        bool: Success status
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            filename = tile_info["filename"]
            bounds = tile_info["bounds"]

            # Count features per risk level
            risk_counts = {"High_risk": 0, "Medium_risk": 0, "Low_risk": 0}
            for feature in geojson_data.get("features", []):
                layer = feature.get("properties", {}).get("layer")
                if layer in risk_counts:
                    risk_counts[layer] += 1

            # Check if tile exists
            cursor.execute(
                "SELECT id FROM climate.inundation_history_tiles WHERE filename = %s",
                (filename,)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE climate.inundation_history_tiles
                    SET geojson_data = %s,
                        feature_count = %s,
                        high_risk_count = %s,
                        medium_risk_count = %s,
                        low_risk_count = %s,
                        updated_at = NOW()
                    WHERE filename = %s
                """, (
                    Json(geojson_data),
                    len(geojson_data.get("features", [])),
                    risk_counts["High_risk"],
                    risk_counts["Medium_risk"],
                    risk_counts["Low_risk"],
                    filename
                ))
            else:
                cursor.execute("""
                    INSERT INTO climate.inundation_history_tiles
                    (filename, min_lat, min_lon, max_lat, max_lon,
                     geojson_data, feature_count,
                     high_risk_count, medium_risk_count, low_risk_count,
                     source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    filename,
                    bounds["min_lat"],
                    bounds["min_lon"],
                    bounds["max_lat"],
                    bounds["max_lon"],
                    Json(geojson_data),
                    len(geojson_data.get("features", [])),
                    risk_counts["High_risk"],
                    risk_counts["Medium_risk"],
                    risk_counts["Low_risk"],
                    "google_gcs"
                ))

            return True

    except Exception as e:
        logger.error(f"Failed to ingest tile {tile_info['filename']}: {e}")
        return False


def sync_inundation_history(max_workers=4, force_update=False):
    """
    Main sync function - downloads and ingests all GHoA tiles.

    Args:
        max_workers: Number of parallel downloads
        force_update: If True, re-download all tiles even if they exist

    Returns:
        dict: Sync statistics
    """
    logger.info("Starting Google Flood Inundation History sync...")

    stats = {
        "total_tiles": 0,
        "downloaded": 0,
        "ingested": 0,
        "skipped": 0,
        "failed": 0,
        "total_size_mb": 0
    }

    # Get list of tiles
    tiles = list_ghoa_tiles()
    stats["total_tiles"] = len(tiles)
    stats["total_size_mb"] = round(sum(t["size_bytes"] for t in tiles) / (1024 * 1024), 2)

    if not tiles:
        logger.warning("No tiles found to sync")
        return stats

    # Check which tiles already exist
    if not force_update:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT filename FROM climate.inundation_history_tiles")
                existing = {row[0] for row in cursor.fetchall()}
                tiles = [t for t in tiles if t["filename"] not in existing]
                stats["skipped"] = stats["total_tiles"] - len(tiles)
                logger.info(f"Skipping {stats['skipped']} already ingested tiles")
        except Exception as e:
            logger.warning(f"Could not check existing tiles: {e}")

    if not tiles:
        logger.info("All tiles already ingested")
        return stats

    # Download and ingest tiles in parallel
    logger.info(f"Downloading {len(tiles)} tiles with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_tile, tile): tile for tile in tiles}

        for future in as_completed(futures):
            tile_info, geojson_data = future.result()

            if geojson_data is None:
                stats["failed"] += 1
                continue

            stats["downloaded"] += 1

            if ingest_inundation_tile(tile_info, geojson_data):
                stats["ingested"] += 1
                logger.info(f"Ingested {tile_info['filename']} ({stats['ingested']}/{len(tiles)})")
            else:
                stats["failed"] += 1

    logger.info(f"Sync complete: {stats['ingested']}/{stats['total_tiles']} tiles ingested, "
                f"{stats['failed']} failed, {stats['skipped']} skipped")

    return stats


def run_gcs_inundation_sync():
    """Entry point for scheduler"""
    try:
        stats = sync_inundation_history()
        return stats["failed"] == 0
    except Exception as e:
        logger.exception(f"GCS inundation sync failed: {e}")
        return False


if __name__ == "__main__":
    # Allow running standalone for testing
    import sys
    force = "--force" in sys.argv
    stats = sync_inundation_history(force_update=force)
    print(json.dumps(stats, indent=2))
