"""Google Drive sync module for Multimodal Ensemble Forecasts"""
import re
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .settings import DRIVE_CONFIG, DB_CONFIG
from .database import get_db_connection, ingest_ensemble_geojson
from .logger_config import setup_logger

logger = setup_logger(__name__, 'drive_sync.log')


class DriveSyncer:
    """Syncs Multimodal Ensemble data from Google Drive to PostgreSQL"""

    def __init__(self):
        self.config = DRIVE_CONFIG
        self.service = None
        self.control_points = {}

    def connect_drive(self):
        """Connect to Google Drive API"""
        try:
            creds_file = self.config.get('credentials_file')
            if not creds_file or not Path(creds_file).exists():
                logger.error(f"Credentials file not found: {creds_file}")
                return False

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            credentials = service_account.Credentials.from_service_account_file(
                creds_file, scopes=SCOPES
            )
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Connected to Google Drive")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Google Drive: {e}")
            return False

    def load_control_points(self):
        """Load ensemble control points from database (with lat/lon geometry)"""
        logger.info("Loading control points from database...")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        point_id,
                        gridcode,
                        admin_name,
                        x,
                        y,
                        zone,
                        is_node,
                        ST_AsGeoJSON(geom) as geometry
                    FROM multimodal_control_points
                    ORDER BY zone, gridcode
                """)

                for row in cursor.fetchall():
                    point_id, gridcode, admin_name, x, y, zone, is_node, geom_json = row
                    geom = json.loads(geom_json)

                    # Key by (zone, gridcode)
                    key = (zone, gridcode)
                    self.control_points[key] = {
                        'point_id': point_id,
                        'gridcode': gridcode,
                        'admin_name': admin_name,
                        'x': x,
                        'y': y,
                        'zone': zone,
                        'is_node': is_node,
                        'geometry': geom
                    }

            logger.info(f"Loaded {len(self.control_points)} control points")
            return True

        except Exception as e:
            logger.error(f"Failed to load control points: {e}")
            return False

    def get_latest_folder(self):
        """Get the most recent dated folder from Drive"""
        folder_id = self.config.get('folder_id')
        if not folder_id:
            logger.error("No DRIVE_FOLDER_ID configured")
            return None

        try:
            # List subfolders
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields='files(id, name)',
                orderBy='name desc'
            ).execute()

            subfolders = results.get('files', [])
            if subfolders:
                latest = subfolders[0]
                logger.info(f"Using folder: {latest['name']}")
                return latest['id']

            # No subfolders, use parent
            return folder_id

        except Exception as e:
            logger.error(f"Failed to get folder: {e}")
            return None

    def list_zone_files(self, folder_id):
        """List all Zone*.csv files in folder"""
        files = []
        page_token = None

        query = f"'{folder_id}' in parents and mimeType='text/csv' and trashed=false"

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

        logger.info(f"Found {len(files)} CSV files")
        return files

    def download_file_content(self, file_id):
        """Download file content to memory"""
        request = self.service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        return fh.read().decode('utf-8')

    def parse_point_csv(self, content, zone, gridcode):
        """Parse individual point CSV file (time series format)

        Format:
        ,Floodproof,GeoSFM,Mike_Hydro_CHIRP,...
        2026-01-02,value1,value2,value3,...
        """
        forecasts = []
        lines = content.strip().split('\n')

        if len(lines) < 2:
            return forecasts

        # Parse header
        header = lines[0].split(',')
        model_cols = header[1:]  # Skip first empty column

        # Parse data rows
        for line in lines[1:]:
            if not line.strip():
                continue

            values = line.split(',')
            if not values:
                continue

            date_str = values[0].strip()
            if not date_str:
                continue

            forecast = {'date': date_str}

            for i, model in enumerate(model_cols):
                if i + 1 < len(values):
                    val = values[i + 1].strip()
                    if val and val != '':
                        try:
                            num = float(val)
                            # Filter placeholder values
                            if num > -1e-10 and num < 1e10:
                                forecast[model] = num
                        except ValueError:
                            pass

            forecasts.append(forecast)

        return forecasts

    def create_geojson(self, forecast_data, data_date):
        """Create GeoJSON by merging forecast data with control points"""
        features = []
        matched = 0

        for key, point in self.control_points.items():
            forecasts = forecast_data.get(key, [])

            feature = {
                'type': 'Feature',
                'geometry': point['geometry'],
                'properties': {
                    'point_id': point['point_id'],
                    'gridcode': point['gridcode'],
                    'admin_name': point['admin_name'],
                    'zone': point['zone'],
                    'x': point['x'],
                    'y': point['y'],
                    'is_node': point['is_node'],
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
                'date': data_date.strftime('%Y-%m-%d'),
                'total_points': len(features),
                'matched_points': matched
            }
        }

        return geojson, len(features), matched

    def sync(self):
        """Main sync function"""
        logger.info("=" * 70)
        logger.info("Multimodal Drive Sync Started")
        logger.info("=" * 70)

        # Connect to Drive
        if not self.connect_drive():
            return False

        # Load control points from DB
        if not self.load_control_points():
            return False

        # Get latest folder
        folder_id = self.get_latest_folder()
        if not folder_id:
            return False

        # List zone files
        files = self.list_zone_files(folder_id)
        if not files:
            logger.warning("No Zone files found")
            return False

        # Pattern for Zone{zone}_{gridcode}.csv
        point_pattern = re.compile(r'Zone(\d+)_(\d+)\.csv', re.IGNORECASE)

        # Stream and parse files
        forecast_data = {}  # {(zone, gridcode): [forecasts]}
        processed = 0

        for file_info in files:
            filename = file_info['name']
            match = point_pattern.match(filename)

            if not match:
                continue

            zone = int(match.group(1))
            gridcode = int(match.group(2))
            key = (zone, gridcode)

            try:
                content = self.download_file_content(file_info['id'])
                forecasts = self.parse_point_csv(content, zone, gridcode)

                if forecasts:
                    forecast_data[key] = forecasts

                processed += 1
                if processed % 200 == 0:
                    logger.info(f"  Progress: {processed}/{len(files)} files")

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

        logger.info(f"Processed {processed} files, {len(forecast_data)} with data")

        # Create GeoJSON
        data_date = datetime.now().date()
        geojson, feature_count, matched_count = self.create_geojson(forecast_data, data_date)

        logger.info(f"Created GeoJSON: {feature_count} features, {matched_count} with data")

        # Ingest to database
        date_string = data_date.strftime('%Y%m%d')
        if ingest_ensemble_geojson(data_date, date_string, geojson, feature_count, matched_count):
            logger.info("Successfully ingested to database")
            return True
        else:
            logger.error("Failed to ingest to database")
            return False


def run_drive_sync():
    """Entry point for Drive sync"""
    syncer = DriveSyncer()
    return syncer.sync()


if __name__ == "__main__":
    run_drive_sync()
