"""Job 1: Merge CSVs with control points and save GeoJSON/GeoParquet back to Drive"""
import re
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from .settings import DRIVE_CONFIG, DATA_DIR
from .database import get_db_connection
from .logger_config import setup_logger

logger = setup_logger(__name__, 'drive_merge.log')


class DriveMergeJob:
    """Merge CSVs with control points in Drive and save GeoJSON/GeoParquet"""

    def __init__(self):
        self.config = DRIVE_CONFIG
        self.service = None

    def connect_drive(self):
        """Connect to Google Drive API with read/write access"""
        try:
            creds_file = self.config.get('credentials_file')
            if not creds_file or not Path(creds_file).exists():
                logger.error(f"Credentials file not found: {creds_file}")
                return False

            SCOPES = ['https://www.googleapis.com/auth/drive']
            credentials = service_account.Credentials.from_service_account_file(
                creds_file, scopes=SCOPES
            )
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Connected to Google Drive")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def load_control_points(self):
        """Load control points from database as DataFrame"""
        logger.info("Loading control points...")
        try:
            with get_db_connection() as conn:
                query = """
                    SELECT point_id, gridcode, admin_name, x, y, zone, is_node,
                           ST_X(geom) as lon, ST_Y(geom) as lat
                    FROM gha.multimodal_control_points
                    ORDER BY zone, gridcode
                """
                df = pd.read_sql(query, conn)

            # Create geometry and join key
            geometry = [Point(xy) for xy in zip(df['lon'], df['lat'])]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
            gdf['join_key'] = gdf['zone'].astype(str) + '_' + gdf['gridcode'].astype(str)

            logger.info(f"Loaded {len(gdf)} control points")
            return gdf
        except Exception as e:
            logger.error(f"Failed to load control points: {e}")
            return None

    def list_date_folders(self):
        """List date folders in Drive"""
        folder_id = self.config.get('folder_id')
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(
            q=query,
            fields='files(id, name, modifiedTime)',
            orderBy='name desc'
        ).execute()
        return results.get('files', [])

    def list_csv_files(self, folder_id):
        """List Zone*.csv files in folder"""
        files = []
        page_token = None
        query = f"'{folder_id}' in parents and name contains 'Zone' and mimeType='text/csv' and trashed=false"

        while True:
            results = self.service.files().list(
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

    def check_merged_exists(self, folder_id, date_str):
        """Check if merged GeoJSON already exists in folder"""
        query = f"'{folder_id}' in parents and name='merged_{date_str}.geojson' and trashed=false"
        results = self.service.files().list(q=query, fields='files(id)').execute()
        return len(results.get('files', [])) > 0

    def download_file_content(self, file_id):
        """Download file content"""
        request = self.service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read().decode('utf-8')

    def upload_file(self, folder_id, filename, content, mimetype):
        """Upload file to Drive folder"""
        # Check if file exists
        query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
        results = self.service.files().list(q=query, fields='files(id)').execute()
        existing = results.get('files', [])

        media = MediaIoBaseUpload(BytesIO(content.encode('utf-8')), mimetype=mimetype)

        if existing:
            # Update existing file
            file_id = existing[0]['id']
            self.service.files().update(fileId=file_id, media_body=media).execute()
            logger.info(f"Updated: {filename}")
        else:
            # Create new file
            metadata = {'name': filename, 'parents': [folder_id]}
            self.service.files().create(body=metadata, media_body=media).execute()
            logger.info(f"Created: {filename}")

    def parse_csv(self, content, zone, gridcode):
        """Parse CSV to list of forecast dicts"""
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return []

        header = lines[0].split(',')
        model_cols = header[1:]

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

    def merge_and_save(self, folder_id, folder_name, control_gdf):
        """Merge CSVs with control points and save to Drive"""
        # Parse date from folder name (format: DDMMYYYY)
        try:
            data_date = datetime.strptime(folder_name, '%d%m%Y').date()
        except:
            logger.error(f"Invalid folder name format: {folder_name}")
            return False

        date_str = data_date.strftime('%Y%m%d')

        # Check if already merged
        if self.check_merged_exists(folder_id, date_str):
            logger.info(f"Merged file already exists for {folder_name}, skipping")
            return True

        # List CSV files
        csv_files = self.list_csv_files(folder_id)
        logger.info(f"Found {len(csv_files)} CSV files in {folder_name}")

        if len(csv_files) < 100:
            logger.warning(f"Too few CSV files ({len(csv_files)}), folder may be incomplete")
            return False

        # Download and parse CSVs
        point_pattern = re.compile(r'Zone(\d+)_(\d+)\.csv', re.IGNORECASE)
        forecast_data = {}  # {join_key: [forecasts]}
        processed = 0

        for file_info in csv_files:
            filename = file_info['name']
            match = point_pattern.match(filename)
            if not match:
                continue

            zone = int(match.group(1))
            gridcode = int(match.group(2))
            join_key = f"{zone}_{gridcode}"

            try:
                content = self.download_file_content(file_info['id'])
                forecasts = self.parse_csv(content, zone, gridcode)
                if forecasts:
                    forecast_data[join_key] = forecasts
                processed += 1
                if processed % 500 == 0:
                    logger.info(f"  Progress: {processed}/{len(csv_files)}")
            except Exception as e:
                pass

        logger.info(f"Processed {processed} files, {len(forecast_data)} with data")

        # Build GeoJSON
        features = []
        matched = 0

        for _, row in control_gdf.iterrows():
            join_key = row['join_key']
            forecasts = forecast_data.get(join_key, [])

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
                    'has_data': len(forecasts) > 0,
                    'forecasts': forecasts
                }
            }
            features.append(feature)
            if forecasts:
                matched += 1

        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'data_date': data_date.strftime('%Y-%m-%d'),
                'total_points': len(features),
                'matched_points': matched
            }
        }

        logger.info(f"Created GeoJSON: {len(features)} features, {matched} with data")

        # Upload GeoJSON to Drive
        geojson_content = json.dumps(geojson)
        self.upload_file(folder_id, f"merged_{date_str}.geojson", geojson_content, 'application/geo+json')

        logger.info(f"SUCCESS: Merged file saved to Drive folder {folder_name}")
        return True

    def run(self, folder_name=None):
        """Run the merge job"""
        logger.info("=" * 70)
        logger.info("Drive Merge Job Started")
        logger.info("=" * 70)

        if not self.connect_drive():
            return False

        control_gdf = self.load_control_points()
        if control_gdf is None:
            return False

        folders = self.list_date_folders()
        if not folders:
            logger.error("No date folders found")
            return False

        logger.info(f"Found {len(folders)} date folders")

        if folder_name:
            # Process specific folder
            target = next((f for f in folders if f['name'] == folder_name), None)
            if not target:
                logger.error(f"Folder {folder_name} not found")
                return False
            return self.merge_and_save(target['id'], target['name'], control_gdf)
        else:
            # Process all folders without merged file (skip first/latest as it may be incomplete)
            success_count = 0
            for folder in folders[1:]:  # Skip latest folder
                if self.merge_and_save(folder['id'], folder['name'], control_gdf):
                    success_count += 1

            logger.info(f"Processed {success_count} folders")
            return success_count > 0


def run_drive_merge(folder_name=None):
    """Entry point"""
    job = DriveMergeJob()
    return job.run(folder_name)


if __name__ == "__main__":
    run_drive_merge()
