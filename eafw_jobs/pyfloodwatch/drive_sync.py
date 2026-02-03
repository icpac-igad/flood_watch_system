"""Google Drive sync module for Multimodal Ensemble Forecasts.

Downloads per-point CSV files from Google Drive and ingests forecast
data into the normalized gha.multimodal_forecasts table.

Uses concurrent downloads (ThreadPoolExecutor) for speed.
"""
import re
import time
from io import BytesIO
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .settings import DRIVE_CONFIG, DB_CONFIG
from .database import get_db_connection, ingest_multimodal_forecasts
from .logger_config import setup_logger

logger = setup_logger(__name__, 'drive_sync.log')

# Concurrent download workers
MAX_WORKERS = 20


class DriveSyncer:
    """Syncs Multimodal Ensemble data from Google Drive to gha schema"""

    def __init__(self):
        self.config = DRIVE_CONFIG
        self.credentials = None
        self.service = None
        self.control_points = {}  # {(zone, gridcode): [point_dicts]}

    def connect_drive(self):
        """Connect to Google Drive API"""
        try:
            creds_file = self.config.get('credentials_file')
            if not creds_file or not Path(creds_file).exists():
                logger.error(f"Credentials file not found: {creds_file}")
                return False

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            self.credentials = service_account.Credentials.from_service_account_file(
                creds_file, scopes=SCOPES
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Connected to Google Drive")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Google Drive: {e}")
            return False

    def _build_service(self):
        """Build a new Drive service instance (thread-safe)."""
        return build('drive', 'v3', credentials=self.credentials)

    def load_control_points(self):
        """Load control points from gha.multimodal_control_points.

        Keys by (zone, gridcode) -> list of point dicts, since zone+gridcode
        can map to multiple point_ids (e.g. zone 6 gridcodes 45, 1435).
        """
        logger.info("Loading control points from gha.multimodal_control_points...")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT point_id, gridcode, admin_name, x, y, zone, is_node
                    FROM gha.multimodal_control_points
                    ORDER BY zone, gridcode, point_id
                """)

                total = 0
                for row in cursor.fetchall():
                    point_id, gridcode, admin_name, x, y, zone, is_node = row
                    key = (zone, gridcode)

                    if key not in self.control_points:
                        self.control_points[key] = []

                    self.control_points[key].append({
                        'point_id': point_id,
                        'gridcode': gridcode,
                        'admin_name': admin_name,
                        'x': x,
                        'y': y,
                        'zone': zone,
                        'is_node': is_node,
                    })
                    total += 1

            logger.info(
                f"Loaded {total} control points "
                f"({len(self.control_points)} unique zone+gridcode keys)"
            )
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
            query = (
                f"'{folder_id}' in parents and "
                f"mimeType='application/vnd.google-apps.folder' and trashed=false"
            )
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

            return folder_id

        except Exception as e:
            logger.error(f"Failed to get folder: {e}")
            return None

    def list_zone_files(self, folder_id):
        """List all Zone*.csv files in folder with pagination"""
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

    def _download_one(self, file_info):
        """Download and parse a single CSV file. Thread-safe."""
        filename = file_info['name']
        point_pattern = re.compile(r'Zone(\d+)_(\d+)\.csv', re.IGNORECASE)
        match = point_pattern.match(filename)
        if not match:
            return None

        zone = int(match.group(1))
        gridcode = int(match.group(2))
        key = (zone, gridcode)

        try:
            svc = self._build_service()
            request = svc.files().get_media(fileId=file_info['id'])
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            content = fh.read().decode('utf-8')

            forecasts = self.parse_point_csv(content)
            if forecasts:
                return (key, forecasts)
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")

        return None

    def parse_point_csv(self, content):
        """Parse individual point CSV file (time series format).

        Format:
            ,Floodproof,GeoSFM,Mike_Hydro_CHIRP,Mike_Hydro_IMERG,Mike_Hydro_RFE,daily_avg,daily_max,daily_min
            2026-01-02,0.0,0.96,0.0,0.083,0.00004,0.208,0.96,0.0

        Returns list of forecast dicts with 'date' and model values.
        """
        forecasts = []
        lines = content.strip().split('\n')

        if len(lines) < 2:
            return forecasts

        header = lines[0].split(',')
        model_cols = header[1:]  # Skip first empty/index column

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
                    if val:
                        try:
                            num = float(val)
                            if num > -1e-10 and num < 1e10:
                                forecast[model] = num
                        except ValueError:
                            pass

            forecasts.append(forecast)

        return forecasts

    def sync(self):
        """Main sync: download CSVs from Drive, ingest to gha.multimodal_forecasts"""
        logger.info("=" * 70)
        logger.info("Multimodal Drive Sync Started")
        logger.info("=" * 70)

        if not self.connect_drive():
            return False

        if not self.load_control_points():
            return False

        folder_id = self.get_latest_folder()
        if not folder_id:
            return False

        files = self.list_zone_files(folder_id)
        if not files:
            logger.warning("No Zone files found")
            return False

        # Concurrent download and parse
        forecast_data = {}
        processed = 0
        errors = 0
        start = time.time()

        logger.info(f"Downloading {len(files)} files with {MAX_WORKERS} workers...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self._download_one, f): f for f in files}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    key, forecasts = result
                    forecast_data[key] = forecasts
                    processed += 1
                else:
                    errors += 1

                total_done = processed + errors
                if total_done % 500 == 0:
                    elapsed = time.time() - start
                    rate = total_done / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"  Progress: {total_done}/{len(files)} "
                        f"({rate:.0f} files/sec)"
                    )

        elapsed = time.time() - start
        logger.info(
            f"Downloaded {processed} files with data, {errors} skipped/errors "
            f"in {elapsed:.1f}s ({len(files) / elapsed:.0f} files/sec)"
        )

        if not forecast_data:
            logger.warning("No forecast data parsed from CSV files")
            return False

        # Ingest to normalized gha.multimodal_forecasts
        data_date = datetime.now().date()
        success, matched = ingest_multimodal_forecasts(
            data_date, forecast_data, self.control_points
        )

        if success:
            logger.info(
                f"Successfully ingested forecasts for {data_date} "
                f"({matched} points matched)"
            )
            return True
        else:
            logger.error("Failed to ingest forecasts")
            return False


def run_drive_sync():
    """Entry point for Drive sync"""
    syncer = DriveSyncer()
    return syncer.sync()


if __name__ == "__main__":
    run_drive_sync()
