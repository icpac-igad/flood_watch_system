"""Google Drive sync module for Multimodal Ensemble Forecasts.

Downloads per-point CSV files from Google Drive and ingests forecast
data into the normalized gha.multimodal_forecasts table.

Uses concurrent downloads (ThreadPoolExecutor) for speed.

Usage:
    # Sync all available folders
    python -m pyfloodwatch.drive_sync --all

    # Sync specific folder by name
    python -m pyfloodwatch.drive_sync 31012026

    # Sync latest folder only (default)
    python -m pyfloodwatch.drive_sync
"""
import re
import sys
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

    def get_all_folders(self):
        """List every dated folder under DRIVE_FOLDER_ID, sorted newest first.

        Drive's API caps each page at ~100 results when no pageSize is given,
        and orderBy='name desc' is alphabetic — which means once you cross
        a month boundary the new folder names (e.g. ``02052026``) sort
        BELOW the old ones (``30042026``) because '0' < '3'. The first
        page therefore drops the most-recent dates off the bottom.

        We page through every result with ``nextPageToken``, then sort by
        the actual parsed date so callers always see the latest folder
        first regardless of API page order.

        Returns:
            list of dicts with ``id``, ``name``, ``data_date`` (date) keys,
            sorted by ``data_date`` descending.
        """
        folder_id = self.config.get('folder_id')
        if not folder_id:
            logger.error("No DRIVE_FOLDER_ID configured")
            return []

        query = (
            f"'{folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.folder' and trashed=false"
        )

        raw_files = []
        page_token = None
        try:
            while True:
                results = self.service.files().list(
                    q=query,
                    fields='nextPageToken, files(id, name)',
                    pageSize=1000,
                    pageToken=page_token,
                ).execute()
                raw_files.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
        except Exception as e:
            logger.error(f"Failed to get folders: {e}")
            return []

        folders = []
        for f in raw_files:
            name = f['name']
            # Folder names are DDMMYYYY (e.g. ``02052026``). Skip anything
            # that doesn't parse — ``_hist`` suffixes, archive folders, etc.
            clean_name = name.replace('_hist', '')
            try:
                data_date = datetime.strptime(clean_name, '%d%m%Y').date()
            except ValueError:
                logger.warning(f"Skipping folder with unparseable name: {name}")
                continue
            folders.append({
                'id': f['id'],
                'name': name,
                'data_date': data_date,
            })

        # Sort by parsed date descending — independent of API result order.
        folders.sort(key=lambda x: x['data_date'], reverse=True)
        return folders

    def get_ingested_dates(self):
        """Get dates that have already been ingested to the database.

        Returns:
            set of date objects
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT data_date FROM gha.multimodal_forecasts
                """)
                return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Failed to get ingested dates: {e}")
            return set()

    def get_latest_folder(self):
        """Get the most recent dated folder from Drive (backwards compatible)"""
        folders = self.get_all_folders()
        if folders:
            latest = folders[0]
            logger.info(f"Using folder: {latest['name']}")
            return latest['id']
        return self.config.get('folder_id')

    def list_zone_files(self, folder_id):
        """List all Zone*.csv files in folder with pagination.

        We used to filter on ``mimeType='text/csv'``, but Drive labels many
        uploaded ``.csv`` files as ``application/vnd.ms-excel`` or
        ``application/octet-stream`` depending on the uploader's OS — that
        filter silently dropped ~70% of yesterday's files. Now we list every
        non-trashed file in the folder and let the ``Zone\\d+_\\d+\\.csv``
        regex in ``_download_one`` keep only the right ones.
        """
        files = []
        page_token = None
        query = f"'{folder_id}' in parents and trashed=false"

        while True:
            results = self.service.files().list(
                q=query,
                fields='nextPageToken, files(id, name, mimeType)',
                pageSize=1000,
                pageToken=page_token
            ).execute()

            for f in results.get('files', []):
                # Keep only files whose name matches the Zone*.csv pattern,
                # regardless of how Drive classified the MIME type.
                if f.get('name', '').lower().endswith('.csv') and f.get('name', '').lower().startswith('zone'):
                    files.append(f)
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

    def sync_folder(self, folder):
        """Sync a single folder to the database.

        Args:
            folder: dict with 'id', 'name', 'data_date' keys

        Returns:
            bool: Success status
        """
        folder_id = folder['id']
        folder_name = folder['name']
        data_date = folder['data_date']

        logger.info(f"Processing folder: {folder_name} (date: {data_date})")

        files = self.list_zone_files(folder_id)
        if not files:
            logger.warning(f"No Zone files found in {folder_name}")
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
            logger.warning(f"No forecast data parsed from {folder_name}")
            return False

        # Ingest to normalized gha.multimodal_forecasts using folder date
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
            logger.error(f"Failed to ingest forecasts for {data_date}")
            return False

    def sync(self, folder_name=None, sync_all=False, days=None):
        """Main sync entry point.

        Args:
            folder_name: Specific folder name to sync (e.g., '31012026')
            sync_all: If True, sync all available folders
            days: Number of recent days to sync (e.g., 7 for last 7 days)

        Returns:
            bool: Success status (True if at least one folder synced)
        """
        logger.info("=" * 70)
        logger.info("Multimodal Drive Sync Started")
        logger.info("=" * 70)

        if not self.connect_drive():
            return False

        if not self.load_control_points():
            return False

        all_folders = self.get_all_folders()
        if not all_folders:
            logger.error("No folders found in Drive")
            return False

        logger.info(f"Found {len(all_folders)} folders in Drive")

        # Determine which folders to process
        if folder_name:
            # Sync specific folder by name
            folders_to_sync = [f for f in all_folders if f['name'] == folder_name]
            if not folders_to_sync:
                logger.error(f"Folder '{folder_name}' not found in Drive")
                logger.info(f"Available folders: {[f['name'] for f in all_folders]}")
                return False
        elif sync_all:
            # Sync all folders, skip already ingested
            ingested = self.get_ingested_dates()
            folders_to_sync = [f for f in all_folders if f['data_date'] not in ingested]
            logger.info(f"Already ingested: {len(ingested)} dates")
            logger.info(f"To sync: {len(folders_to_sync)} folders")
        elif days:
            # Sync last N days
            from datetime import timedelta
            today = datetime.now().date()
            cutoff = today - timedelta(days=days)
            folders_to_sync = [f for f in all_folders if f['data_date'] >= cutoff]
            logger.info(f"Syncing folders from last {days} days ({len(folders_to_sync)} folders)")
        else:
            # Default: sync today's folder or latest if today not found
            today = datetime.now().date()
            folders_to_sync = [f for f in all_folders if f['data_date'] == today]
            if not folders_to_sync:
                # Fall back to latest
                folders_to_sync = [all_folders[0]]
                logger.info(f"No folder for today, using latest: {folders_to_sync[0]['name']}")

        if not folders_to_sync:
            logger.info("No folders to sync (all already processed)")
            return True

        # Process each folder
        success_count = 0
        for folder in folders_to_sync:
            logger.info("-" * 70)
            if self.sync_folder(folder):
                success_count += 1

        logger.info("=" * 70)
        logger.info(f"Sync complete: {success_count}/{len(folders_to_sync)} folders processed")
        logger.info("=" * 70)

        return success_count > 0


def run_drive_sync(folder_name=None, sync_all=False, days=None):
    """Entry point for Drive sync.

    Args:
        folder_name: Specific folder name to sync
        sync_all: If True, sync all available folders
        days: Number of recent days to sync
    """
    syncer = DriveSyncer()
    return syncer.sync(folder_name=folder_name, sync_all=sync_all, days=days)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Sync multimodal forecasts from Google Drive')
    parser.add_argument('folder', nargs='?', help='Specific folder name to sync (e.g., 31012026)')
    parser.add_argument('--all', '-a', action='store_true', help='Sync all available folders')
    parser.add_argument('--days', '-d', type=int, help='Sync last N days')

    args = parser.parse_args()

    if args.all:
        run_drive_sync(sync_all=True)
    elif args.days:
        run_drive_sync(days=args.days)
    elif args.folder:
        run_drive_sync(folder_name=args.folder)
    else:
        # Default: sync today or latest
        run_drive_sync()
