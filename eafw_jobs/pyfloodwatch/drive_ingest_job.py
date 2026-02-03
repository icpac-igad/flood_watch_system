"""Job 2: Push merged GeoJSON from Drive to Database"""
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .settings import DRIVE_CONFIG
from .database import ingest_ensemble_geojson
from .logger_config import setup_logger

logger = setup_logger(__name__, 'drive_ingest.log')


class DriveIngestJob:
    """Push merged GeoJSON files from Drive to Database"""

    def __init__(self):
        self.config = DRIVE_CONFIG
        self.service = None

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
            logger.error(f"Failed to connect: {e}")
            return False

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

    def find_merged_file(self, folder_id):
        """Find merged GeoJSON file in folder"""
        query = f"'{folder_id}' in parents and name contains 'merged_' and name contains '.geojson' and trashed=false"
        results = self.service.files().list(
            q=query,
            fields='files(id, name, modifiedTime)'
        ).execute()
        files = results.get('files', [])
        return files[0] if files else None

    def download_geojson(self, file_id):
        """Download and parse GeoJSON file"""
        request = self.service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        content = fh.read().decode('utf-8')
        return json.loads(content)

    def ingest_folder(self, folder_id, folder_name):
        """Ingest merged GeoJSON from folder to database"""
        # Find merged file
        merged_file = self.find_merged_file(folder_id)
        if not merged_file:
            logger.info(f"No merged file in {folder_name}")
            return False

        logger.info(f"Found merged file: {merged_file['name']}")

        # Download GeoJSON
        try:
            geojson = self.download_geojson(merged_file['id'])
        except Exception as e:
            logger.error(f"Failed to download: {e}")
            return False

        # Extract metadata
        props = geojson.get('properties', {})
        data_date_str = props.get('data_date')
        total_points = props.get('total_points', len(geojson.get('features', [])))
        matched_points = props.get('matched_points', 0)

        # Parse date
        if data_date_str:
            data_date = datetime.strptime(data_date_str, '%Y-%m-%d').date()
        else:
            # Try to parse from folder name (DDMMYYYY)
            try:
                data_date = datetime.strptime(folder_name, '%d%m%Y').date()
            except:
                logger.error(f"Cannot determine date for {folder_name}")
                return False

        date_string = data_date.strftime('%Y%m%d')

        logger.info(f"Ingesting: date={data_date}, features={total_points}, matched={matched_points}")

        # Ingest to database
        if ingest_ensemble_geojson(data_date, date_string, geojson, total_points, matched_points):
            logger.info(f"SUCCESS: Ingested {folder_name} to database")
            return True
        else:
            logger.error(f"Failed to ingest {folder_name}")
            return False

    def run(self, folder_name=None, ingest_all=False):
        """Run the ingest job"""
        logger.info("=" * 70)
        logger.info("Drive Ingest Job Started")
        logger.info("=" * 70)

        if not self.connect_drive():
            return False

        folders = self.list_date_folders()
        if not folders:
            logger.error("No date folders found")
            return False

        logger.info(f"Found {len(folders)} date folders")

        if folder_name:
            # Ingest specific folder
            target = next((f for f in folders if f['name'] == folder_name), None)
            if not target:
                logger.error(f"Folder {folder_name} not found")
                return False
            return self.ingest_folder(target['id'], target['name'])

        elif ingest_all:
            # Ingest all folders with merged files
            success_count = 0
            for folder in folders:
                if self.ingest_folder(folder['id'], folder['name']):
                    success_count += 1
            logger.info(f"Ingested {success_count} folders")
            return success_count > 0

        else:
            # Ingest latest folder with merged file
            for folder in folders:
                merged = self.find_merged_file(folder['id'])
                if merged:
                    return self.ingest_folder(folder['id'], folder['name'])

            logger.warning("No folders with merged files found")
            return False


def run_drive_ingest(folder_name=None, ingest_all=False):
    """Entry point"""
    job = DriveIngestJob()
    return job.run(folder_name, ingest_all)


if __name__ == "__main__":
    run_drive_ingest()
