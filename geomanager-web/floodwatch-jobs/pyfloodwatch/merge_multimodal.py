#!/usr/bin/env python
"""
Simple script to merge multimodal CSVs with control points.

Usage:
    python -m pyfloodwatch.merge_multimodal 04012026
    python -m pyfloodwatch.merge_multimodal  # uses latest complete folder
"""
import sys
import re
import json
import tempfile
import shutil
from io import BytesIO
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Number of parallel download threads
NUM_WORKERS = 50

from .settings import DRIVE_CONFIG, DATA_DIR
from .database import get_db_connection

# Thread-local storage for Drive service (thread-safe)
import threading
_thread_local = threading.local()

def get_thread_service():
    """Get or create a Drive service for current thread"""
    if not hasattr(_thread_local, 'service'):
        creds_file = DRIVE_CONFIG.get('credentials_file')
        SCOPES = ['https://www.googleapis.com/auth/drive']
        credentials = service_account.Credentials.from_service_account_file(
            creds_file, scopes=SCOPES
        )
        _thread_local.service = build('drive', 'v3', credentials=credentials)
    return _thread_local.service

# ============================================================================
# STEP 1: Load control points from DB
# ============================================================================
# Control points are the spatial reference for multimodal forecast data.
# Each point has:
#   - zone: geographic zone (1-6)
#   - gridcode: unique ID within zone
#   - lon/lat: coordinates for mapping
#   - admin_name: administrative area name
#
# The join_key (zone_gridcode) links control points to CSV forecast files.
# Example: Zone1_123 -> join_key = "1_123"
# ============================================================================
def load_control_points():
    """Load control points from database as GeoDataFrame"""
    print("STEP 1: Loading control points from database...")

    with get_db_connection() as conn:
        query = """
            SELECT point_id, gridcode, admin_name, x, y, zone, is_node,
                   ST_X(geom) as lon, ST_Y(geom) as lat
            FROM public.multimodal_control_points
            ORDER BY zone, gridcode
        """
        df = pd.read_sql(query, conn)

    # Create geometry
    geometry = [Point(xy) for xy in zip(df['lon'], df['lat'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # Create join key: zone_gridcode
    gdf['join_key'] = gdf['zone'].astype(str) + '_' + gdf['gridcode'].astype(str)

    print(f"  ✓ Loaded {len(gdf)} control points")
    return gdf


# ============================================================================
# STEP 2: Connect to Drive and download CSVs
# ============================================================================
# Google Drive contains date folders (e.g., 04012026 = Jan 4, 2026)
# Each folder has ~3173 CSV files named: Zone{zone}_{gridcode}.csv
#
# CSV format:
#   ,Floodproof,GeoSFM,Mike_Hydro_CHIRP,Mike_Hydro_IMERG,Mike_Hydro_RFE,daily_avg,daily_max,daily_min
#   2026-01-07,0.0,0.96,0.0,0.083,0.00004,0.208,0.96,0.0
#   2026-01-08,0.0,0.96,0.0,0.080,0.00004,0.208,0.96,0.0
#   ...
#
# Each CSV contains forecast values from 5 hydrological models for ~14 days.
# ============================================================================
def connect_drive():
    """Connect to Google Drive"""
    print("STEP 2: Connecting to Google Drive...")

    creds_file = DRIVE_CONFIG.get('credentials_file')
    SCOPES = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_file(
        creds_file, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
    print("  ✓ Connected")
    return service


def list_folders(service):
    """List date folders"""
    folder_id = DRIVE_CONFIG.get('folder_id')
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        fields='files(id, name)',
        orderBy='name desc'
    ).execute()
    return results.get('files', [])


def list_csvs(service, folder_id):
    """List Zone*.csv files in folder"""
    files = []
    page_token = None
    query = f"'{folder_id}' in parents and name contains 'Zone' and mimeType='text/csv' and trashed=false"

    while True:
        results = service.files().list(
            q=query,
            fields='nextPageToken, files(id, name)',
            pageSize=1000,
            pageToken=page_token
        ).execute()
        files.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return files


def download_csv(service, file_id):
    """Download CSV content"""
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read().decode('utf-8')


def parse_csv(content):
    """Parse CSV to list of forecast dicts"""
    lines = content.strip().split('\n')
    if len(lines) < 2:
        return []

    header = lines[0].split(',')
    model_cols = header[1:]  # Skip first column (date)

    forecasts = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = line.split(',')
        if not values[0].strip():
            continue

        row = {'date': values[0].strip()}
        for i, model in enumerate(model_cols):
            if i + 1 < len(values):
                val = values[i + 1].strip()
                if val:
                    try:
                        num = float(val)
                        if -1e-10 < num < 1e10:
                            row[model] = num
                    except:
                        pass
        forecasts.append(row)
    return forecasts


def download_and_parse_single(file_info, point_pattern):
    """Download and parse a single CSV file (for parallel execution)"""
    filename = file_info['name']
    match = point_pattern.match(filename)
    if not match:
        return None, None

    zone = int(match.group(1))
    gridcode = int(match.group(2))
    join_key = f"{zone}_{gridcode}"

    try:
        # Use thread-local service for thread safety
        service = get_thread_service()
        content = download_csv(service, file_info['id'])
        forecasts = parse_csv(content)
        if forecasts:
            return join_key, forecasts
    except Exception:
        pass

    return join_key, None


def download_all_csvs(service, folder_id, folder_name):
    """Download all CSVs in parallel, parse, return forecast data"""
    print(f"  Downloading CSVs from folder {folder_name}...")

    csv_files = list_csvs(service, folder_id)
    print(f"  Found {len(csv_files)} CSV files")
    print(f"  Using {NUM_WORKERS} parallel workers...")

    point_pattern = re.compile(r'Zone(\d+)_(\d+)\.csv', re.IGNORECASE)
    forecast_data = {}  # {join_key: [forecasts]}

    completed = 0
    failed = 0

    # Parallel download using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all download tasks (each thread uses its own Drive service)
        future_to_file = {
            executor.submit(download_and_parse_single, file_info, point_pattern): file_info
            for file_info in csv_files
        }

        # Process completed downloads
        for future in as_completed(future_to_file):
            completed += 1
            try:
                join_key, forecasts = future.result()
                if join_key and forecasts:
                    forecast_data[join_key] = forecasts
            except Exception:
                failed += 1

            # Progress update every 100 files
            if completed % 100 == 0:
                print(f"    Progress: {completed}/{len(csv_files)} ({len(forecast_data)} with data, {failed} failed)")

    print(f"  ✓ Processed {completed} files: {len(forecast_data)} with data, {failed} failed")
    return forecast_data


# ============================================================================
# STEP 3: Key-based join
# ============================================================================
# Join control points (with geometry) to forecast data (from CSVs) using:
#   join_key = "{zone}_{gridcode}"
#
# Control points table:          CSV files:
#   zone | gridcode | lon | lat     Zone1_123.csv -> forecasts for point 1_123
#   1    | 123      | 34.5| 2.3     Zone2_456.csv -> forecasts for point 2_456
#
# Result: Each control point gets its forecasts array attached.
# Points without matching CSV get empty forecasts [].
# ============================================================================
def merge_data(control_gdf, forecast_data):
    """Merge control points with forecast data using join_key"""
    print("STEP 3: Key-based join (zone_gridcode)...")

    # Convert forecast_data to DataFrame for merge
    forecast_records = []
    for join_key, forecasts in forecast_data.items():
        forecast_records.append({
            'join_key': join_key,
            'forecasts': forecasts
        })

    forecast_df = pd.DataFrame(forecast_records)

    # Merge
    merged = control_gdf.merge(forecast_df, on='join_key', how='left')

    # Fill missing with empty list
    merged['forecasts'] = merged['forecasts'].apply(lambda x: x if isinstance(x, list) else [])
    merged['has_data'] = merged['forecasts'].apply(lambda x: len(x) > 0)

    total_points = len(merged)
    matched = merged['has_data'].sum()
    csv_count = len(forecast_data)

    # Show key join status
    if matched == total_points and matched == csv_count:
        print(f"  ✓ ALL JOINED: {csv_count} CSVs → {total_points} control points (100%)")
    elif matched == csv_count:
        print(f"  ✓ Key join: {csv_count} CSVs → {matched}/{total_points} points ({total_points - matched} points have no CSV)")
    else:
        print(f"  ⚠ Partial join: {matched}/{total_points} points, {csv_count} CSVs")
        unmatched_csvs = csv_count - matched
        if unmatched_csvs > 0:
            print(f"    {unmatched_csvs} CSVs did not match any control point")

    return merged


# ============================================================================
# STEP 4: Create GeoJSON + GeoParquet
# ============================================================================
# Output 1: GeoJSON (merged_YYYYMMDD.geojson)
#   - Standard format for web maps and GIS tools
#   - Each feature has geometry + properties including forecasts array
#   - Used for database ingestion and visualization
#
# Output 2: GeoParquet (merged_YYYYMMDD.parquet)
#   - Efficient columnar format for big data
#   - Faster to read/write than GeoJSON
#   - Forecasts stored as JSON string in forecasts_json column
#
# Both files saved locally first, then uploaded to Drive.
# ============================================================================
def create_outputs(merged_gdf, data_date, output_dir):
    """Create GeoJSON and GeoParquet files"""
    print("STEP 4: Creating GeoJSON and GeoParquet...")

    date_str = data_date.strftime('%Y%m%d')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build GeoJSON
    features = []
    for _, row in merged_gdf.iterrows():
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(row['lon']), float(row['lat'])]
            },
            'properties': {
                'point_id': int(row['point_id']),
                'zone': int(row['zone']),
                'gridcode': int(row['gridcode']),
                'admin_name': str(row['admin_name']),
                'x': float(row['x']),
                'y': float(row['y']),
                'is_node': bool(row['is_node']),
                'has_data': bool(row['has_data']),
                'forecasts': row['forecasts']
            }
        }
        features.append(feature)

    matched = sum(1 for f in features if f['properties']['has_data'])

    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'properties': {
            'data_date': data_date.strftime('%Y-%m-%d'),
            'total_points': len(features),
            'matched_points': matched
        }
    }

    # Save GeoJSON
    geojson_path = output_dir / f"merged_{date_str}.geojson"
    with open(geojson_path, 'w') as f:
        json.dump(geojson, f)
    print(f"  ✓ GeoJSON saved: {geojson_path}")

    # Save GeoParquet
    parquet_gdf = merged_gdf.copy()
    parquet_gdf['forecasts_json'] = parquet_gdf['forecasts'].apply(json.dumps)
    parquet_gdf = parquet_gdf.drop(columns=['forecasts'])

    parquet_path = output_dir / f"merged_{date_str}.parquet"
    parquet_gdf.to_parquet(parquet_path, index=False)
    print(f"  ✓ GeoParquet saved: {parquet_path}")

    return geojson_path, parquet_path, geojson


# ============================================================================
# STEP 5: Upload to Drive
# ============================================================================
# Upload merged GeoJSON and GeoParquet back to the same Drive folder.
# This allows:
#   - Other jobs to pick up merged files for DB ingestion
#   - Archive of processed data by date
#   - Sharing merged data with other systems
#
# Files are updated if they already exist (no duplicates created).
# ============================================================================
def upload_to_drive(service, folder_id, file_path, mimetype):
    """Upload file to Drive folder"""
    filename = file_path.name

    # Check if exists
    query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields='files(id)').execute()
    existing = results.get('files', [])

    with open(file_path, 'rb') as f:
        media = MediaIoBaseUpload(BytesIO(f.read()), mimetype=mimetype)

    if existing:
        service.files().update(fileId=existing[0]['id'], media_body=media).execute()
        print(f"  ✓ Updated in Drive: {filename}")
    else:
        metadata = {'name': filename, 'parents': [folder_id]}
        service.files().create(body=metadata, media_body=media).execute()
        print(f"  ✓ Uploaded to Drive: {filename}")


def upload_outputs(service, folder_id, geojson_path, parquet_path):
    """Upload GeoJSON and GeoParquet to Drive (optional - may fail on permissions)"""
    print("STEP 5: Uploading to Drive...")

    try:
        upload_to_drive(service, folder_id, geojson_path, 'application/geo+json')
        upload_to_drive(service, folder_id, parquet_path, 'application/octet-stream')
        print("  ✓ All files uploaded")
        return True
    except Exception as e:
        print(f"  ⚠ Drive upload failed (permissions?): {e}")
        print("  Skipping Drive upload, continuing with database ingestion...")
        return False


# ============================================================================
# STEP 6: Ingest to Database
# ============================================================================
# Store the merged GeoJSON in the database for the map viewer.
# Table: home_multimodal_forecast_geojson
# The materialized view multimodal_points reads from this table.
# ============================================================================
from .database import ingest_multimodal_geojson

def ingest_to_database(geojson, data_date):
    """Ingest merged GeoJSON to database"""
    print("STEP 6: Ingesting to database...")

    date_string = data_date.strftime('%Y%m%d')
    feature_count = len(geojson.get('features', []))
    matched_count = geojson.get('properties', {}).get('matched_points', 0)

    success = ingest_multimodal_geojson(data_date, date_string, geojson, feature_count, matched_count)

    if success:
        print(f"  ✓ Ingested {matched_count}/{feature_count} features to database")
    else:
        print(f"  ✗ Database ingestion failed")

    return success


# ============================================================================
# MAIN
# ============================================================================
def main(folder_name=None):
    """Main function"""
    print("=" * 60)
    print("MULTIMODAL MERGE SCRIPT")
    print("=" * 60)

    # Step 1: Load control points
    control_gdf = load_control_points()

    # Step 2: Connect to Drive
    service = connect_drive()

    # Get folder
    folders = list_folders(service)
    print(f"  Available folders: {[f['name'] for f in folders]}")

    if folder_name:
        folder = next((f for f in folders if f['name'] == folder_name), None)
        if not folder:
            print(f"  ERROR: Folder {folder_name} not found")
            return
    else:
        # Use second latest (first might be incomplete)
        folder = folders[1] if len(folders) > 1 else folders[0]

    print(f"  Using folder: {folder['name']}")

    # Parse date from folder name (DDMMYYYY)
    data_date = datetime.strptime(folder['name'], '%d%m%Y').date()

    # Download CSVs
    forecast_data = download_all_csvs(service, folder['id'], folder['name'])

    # Step 3: Merge
    merged_gdf = merge_data(control_gdf, forecast_data)

    # Step 4: Create outputs
    output_dir = DATA_DIR / 'merged'
    geojson_path, parquet_path, geojson = create_outputs(merged_gdf, data_date, output_dir)

    # Step 5: Upload to Drive (optional - may fail on permissions)
    upload_outputs(service, folder['id'], geojson_path, parquet_path)

    # Step 6: Ingest to database
    ingest_to_database(geojson, data_date)

    print()
    print("=" * 60)
    print("DONE!")
    print(f"  Data date: {data_date}")
    print(f"  Total points: {len(merged_gdf)}")
    print(f"  Points with data: {merged_gdf['has_data'].sum()}")
    print("=" * 60)

    return geojson


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    main(folder)
