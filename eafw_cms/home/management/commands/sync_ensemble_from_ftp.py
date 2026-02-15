"""
Django Management Command: Sync Multimodal Forecasts from FTP/Drive to Database

Downloads Zone*.csv files from FTP or Google Drive, merges with ensemble control points,
and saves as GeoJSON to the database.

Multi-Model: Combines forecasts from multiple models (GFS, ICON, etc.)

Supported Sources:
- FTP: Connect to FTP server and download files
- Google Drive: Download from shared Drive folder
- Local: Use local filesystem files

Data Flow:
1. Connect to source (FTP/Drive/Local)
2. Download Zone*.csv files
3. Merge CSV data with floodproofs_ensemble_points geometries
4. Create GeoJSON FeatureCollection
5. Save to home_ensemble_forecast_geojson table

Usage:
    python manage.py sync_ensemble_from_ftp                       # FTP (default)
    python manage.py sync_ensemble_from_ftp --source drive        # Google Drive
    python manage.py sync_ensemble_from_ftp --source local        # Local files
    python manage.py sync_ensemble_from_ftp --date 2025-12-01
    python manage.py sync_ensemble_from_ftp --days 7
    python manage.py sync_ensemble_from_ftp --zone 1              # Only Zone 1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from ftplib import FTP
from pathlib import Path
from datetime import datetime, timedelta
import csv
import json
import os
import re
import tempfile
import shutil
from io import StringIO
import logging

# Google Drive imports (optional - graceful fallback if not installed)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync GeoSFM ensemble forecasts from FTP to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['ftp', 'drive', 'local'],
            default='ftp',
            help='Data source: ftp (default), drive (Google Drive), local',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to sync (YYYY-MM-DD format)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of recent days to sync (default: 30)',
        )
        parser.add_argument(
            '--zone',
            type=int,
            help='Only download files for specific zone (1-6)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-download even if data already exists',
        )
        parser.add_argument(
            '--local',
            action='store_true',
            help='Use local filesystem instead of FTP (deprecated, use --source local)',
        )
        parser.add_argument(
            '--cache-dir',
            type=str,
            default='/tmp/multimodal_cache',
            help='Local directory to cache downloaded files',
        )
        parser.add_argument(
            '--drive-folder-id',
            type=str,
            help='Google Drive folder ID (for --source drive)',
        )
        parser.add_argument(
            '--keep-temp',
            action='store_true',
            help='Keep temporary files after processing',
        )

    def handle(self, *args, **options):
        # Determine source (--local flag is deprecated, map to source)
        source = options['source']
        if options['local']:
            source = 'local'

        source_labels = {
            'ftp': 'FTP Server',
            'drive': 'Google Drive',
            'local': 'Local Filesystem'
        }

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS(f' Multimodal Forecast Sync: {source_labels[source]} → Database'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        self.source = source

        # FTP configuration from environment
        self.ftp_config = {
            'host': os.getenv('MULTIMODAL_FTP_HOST', os.getenv('ENSEMBLE_FTP_HOST')),
            'port': int(os.getenv('MULTIMODAL_FTP_PORT', os.getenv('ENSEMBLE_FTP_PORT', 21))),
            'user': os.getenv('MULTIMODAL_FTP_USER', os.getenv('ENSEMBLE_FTP_USER')),
            'password': os.getenv('MULTIMODAL_FTP_PASSWORD', os.getenv('ENSEMBLE_FTP_PASSWORD')),
            'remote_dir': os.getenv('MULTIMODAL_FTP_DIR', os.getenv('ENSEMBLE_FTP_DIR', '/ftproot/output/Combined'))
        }

        # Google Drive configuration
        self.drive_config = {
            'folder_id': options.get('drive_folder_id') or os.getenv('MULTIMODAL_DRIVE_FOLDER_ID'),
            'credentials_file': os.getenv('GOOGLE_CREDENTIALS_FILE', '/app/credentials/google-credentials.json'),
        }

        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix='ensemble_ftp_'))
        self.cache_dir = Path(options['cache_dir'])
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f'📁 Temp directory: {self.temp_dir}')
        self.stdout.write(f'📁 Cache directory: {self.cache_dir}\n')

        try:
            # Step 1: Load control points from database
            control_points = self.load_control_points()
            if not control_points:
                self.stdout.write(self.style.ERROR('❌ No control points found!'))
                return

            # Step 2: Determine dates to sync
            dates_to_sync = self.get_dates_to_sync(options)
            self.stdout.write(f'\n📅 Will process {len(dates_to_sync)} dates\n')

            # Step 3: Process each date
            synced_count = 0
            skipped_count = 0
            error_count = 0

            for date_obj in dates_to_sync:
                try:
                    result = self.process_date(date_obj, control_points, options)
                    if result == 'synced':
                        synced_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ❌ Error processing {date_obj.date()}: {e}'))
                    logger.exception(f'Error processing {date_obj.date()}')
                    error_count += 1

            # Step 4: Cleanup
            if not options['keep_temp']:
                shutil.rmtree(self.temp_dir)
                self.stdout.write(f'\n🗑️  Cleaned up temp directory')
            else:
                self.stdout.write(f'\n📂 Temp files kept at: {self.temp_dir}')

            # Summary
            self.stdout.write(self.style.SUCCESS('\n' + '='*70))
            self.stdout.write(self.style.SUCCESS('✅ SYNC COMPLETE'))
            self.stdout.write(f'   Synced:  {synced_count}')
            self.stdout.write(f'   Skipped: {skipped_count}')
            self.stdout.write(f'   Errors:  {error_count}')
            self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Fatal error: {e}'))
            logger.exception('Fatal error in ensemble sync')

    def load_control_points(self):
        """Load ensemble control points from database"""
        self.stdout.write('STEP 1: Loading ensemble control points from database...')

        try:
            with connection.cursor() as cursor:
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
                    FROM floodproofs_ensemble_points
                    ORDER BY zone, gridcode
                """)

                control_points = {}
                for row in cursor.fetchall():
                    point_id, gridcode, admin_name, x, y, zone, is_node, geom_json = row
                    geom = json.loads(geom_json)

                    # Key by (zone, gridcode) since gridcode repeats across zones
                    key = (zone, gridcode)
                    control_points[key] = {
                        'point_id': point_id,
                        'gridcode': gridcode,
                        'admin_name': admin_name,
                        'x': x,
                        'y': y,
                        'zone': zone,
                        'is_node': is_node,
                        'geometry': geom
                    }

            self.stdout.write(self.style.SUCCESS(
                f'  ✅ Loaded {len(control_points)} control points from database\n'
            ))
            return control_points

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Database error: {e}'))
            logger.exception('Error loading control points')
            return None

    def get_dates_to_sync(self, options):
        """Determine which dates to process"""
        if options['date']:
            try:
                date_obj = datetime.strptime(options['date'], '%Y-%m-%d')
                return [date_obj]
            except ValueError:
                self.stdout.write(self.style.ERROR(
                    f'Invalid date format: {options["date"]}. Use YYYY-MM-DD'
                ))
                return []
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=options['days'])
            return [start_date + timedelta(days=x)
                   for x in range((end_date - start_date).days + 1)]

    def process_date(self, date_obj, control_points, options):
        """Process ensemble forecast for a specific date"""
        date_str = date_obj.strftime('%Y%m%d')  # YYYYMMDD for filenames
        date_iso = date_obj.strftime('%Y-%m-%d')

        self.stdout.write(f'\n📅 Processing {date_iso}...')

        # Check if already exists
        if not options['force']:
            if self.check_exists(date_obj):
                self.stdout.write(f'  ⏭️  Already in database (use --force to overwrite)')
                return 'skipped'

        # Download/load Zone CSV files based on source
        if self.source == 'ftp':
            zone_files = self.download_ftp_files(date_str, options.get('zone'))
        elif self.source == 'drive':
            zone_files = self.download_drive_files(date_str, options.get('zone'))
        else:  # local
            zone_files = self.load_local_files(date_str, options.get('zone'))

        if not zone_files:
            self.stdout.write(self.style.WARNING(f'  ⚠️  No Zone files found'))
            return 'error'

        # Parse and merge data
        geojson = self.create_geojson(zone_files, control_points, date_obj)
        if not geojson:
            return 'error'

        # Save to database
        if self.save_to_database(geojson, date_obj):
            self.stdout.write(self.style.SUCCESS(f'  ✅ Synced {date_iso}'))
            return 'synced'
        else:
            return 'error'

    def download_ftp_files(self, date_str, zone_filter=None):
        """Download Zone*.csv files from FTP"""
        self.stdout.write(f'  📥 Connecting to FTP server...')

        zone_files = []
        try:
            ftp = FTP()
            ftp.connect(self.ftp_config['host'], self.ftp_config['port'], timeout=30)
            ftp.login(self.ftp_config['user'], self.ftp_config['password'])
            ftp.set_pasv(True)
            ftp.cwd(self.ftp_config['remote_dir'])

            # List files
            all_files = ftp.nlst()
            # Pattern: Zone1_20251201.csv or Zone1.csv
            patterns = [
                re.compile(rf'Zone(\d+)_{date_str}\.csv', re.IGNORECASE),
                re.compile(rf'Zone(\d+)\.csv', re.IGNORECASE),
            ]

            for filename in all_files:
                for pattern in patterns:
                    match = pattern.match(filename)
                    if match:
                        zone_num = int(match.group(1))

                        # Apply zone filter
                        if zone_filter and zone_num != zone_filter:
                            continue

                        # Download
                        self.stdout.write(f'    📄 Downloading {filename}...')
                        lines = []
                        ftp.retrlines(f'RETR {filename}', lines.append)
                        csv_content = '\n'.join(lines)

                        # Cache locally
                        cache_file = self.cache_dir / f'Zone{zone_num}_{date_str}.csv'
                        cache_file.write_text(csv_content)

                        zone_files.append({
                            'zone': zone_num,
                            'filename': filename,
                            'content': csv_content
                        })
                        break

            ftp.quit()
            self.stdout.write(self.style.SUCCESS(f'  ✅ Downloaded {len(zone_files)} Zone files'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ FTP error: {e}'))
            logger.error(f'FTP error: {e}')

        return zone_files

    def download_drive_files(self, date_str, zone_filter=None):
        """Stream Zone*.csv files from Google Drive directly into memory.

        Does NOT download to local disk - streams directly and returns parsed data.

        Supports point format: Zone{zone}_{gridcode}.csv - each file is a point with time series.

        Requires:
        - google-api-python-client, google-auth packages installed
        - Service account JSON credentials file
        - Folder shared with the service account email
        """
        self.stdout.write(f'  📥 Connecting to Google Drive...')

        if not GOOGLE_DRIVE_AVAILABLE:
            self.stdout.write(self.style.ERROR(
                '  ❌ Google Drive API not available. Install: pip install google-api-python-client google-auth'
            ))
            return []

        zone_files = []

        try:
            # Get credentials file path
            creds_file = self.drive_config.get('credentials_file')
            folder_id = self.drive_config.get('folder_id')

            if not folder_id:
                self.stdout.write(self.style.ERROR(
                    '  ❌ No folder ID. Set MULTIMODAL_DRIVE_FOLDER_ID or use --drive-folder-id'
                ))
                return []

            if not creds_file or not Path(creds_file).exists():
                self.stdout.write(self.style.ERROR(
                    f'  ❌ Credentials file not found: {creds_file}'
                ))
                return []

            # Authenticate with service account
            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            credentials = service_account.Credentials.from_service_account_file(
                creds_file, scopes=SCOPES
            )
            service = build('drive', 'v3', credentials=credentials)

            self.stdout.write(self.style.SUCCESS('  ✅ Connected to Google Drive'))

            # Check if folder contains subfolders (dated folders like 02012026)
            subfolder_query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            subfolder_results = service.files().list(
                q=subfolder_query,
                fields='files(id, name)',
                orderBy='name desc'
            ).execute()
            subfolders = subfolder_results.get('files', [])

            # If there are dated subfolders, use the most recent one
            target_folder_id = folder_id
            if subfolders:
                target_folder_id = subfolders[0]['id']
                self.stdout.write(f'  📂 Using subfolder: {subfolders[0]["name"]}')

            # List CSV files in target folder (with pagination)
            query = f"'{target_folder_id}' in parents and mimeType='text/csv' and trashed=false"
            files = []
            page_token = None

            while True:
                results = service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name)',
                    orderBy='name',
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                files.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            self.stdout.write(f'  📂 Found {len(files)} CSV files in Drive')

            # Pattern for point format: Zone{zone}_{gridcode}.csv
            point_pattern = re.compile(r'Zone(\d+)_(\d+)\.csv', re.IGNORECASE)

            # Filter files matching the pattern
            files_to_process = []
            for file_info in files:
                filename = file_info['name']
                match = point_pattern.match(filename)
                if match:
                    zone_num = int(match.group(1))
                    gridcode = int(match.group(2))

                    # Apply zone filter
                    if zone_filter and zone_num != zone_filter:
                        continue

                    files_to_process.append({
                        'file_id': file_info['id'],
                        'filename': filename,
                        'zone': zone_num,
                        'gridcode': gridcode
                    })

            self.stdout.write(f'  📊 Processing {len(files_to_process)} point files...')

            # Sequential download (thread-safe) with progress
            for i, file_info in enumerate(files_to_process):
                try:
                    request = service.files().get_media(fileId=file_info['file_id'])
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                    fh.seek(0)

                    zone_files.append({
                        'zone': file_info['zone'],
                        'gridcode': file_info['gridcode'],
                        'filename': file_info['filename'],
                        'content': fh.read().decode('utf-8'),
                        'format': 'point'
                    })

                except Exception as e:
                    logger.error(f"Error downloading {file_info['filename']}: {e}")

                # Progress every 200 files
                if (i + 1) % 200 == 0:
                    self.stdout.write(f'    📊 Progress: {i + 1}/{len(files_to_process)} files')

            self.stdout.write(self.style.SUCCESS(f'  ✅ Streamed {len(zone_files)} Zone files from Drive'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Google Drive error: {e}'))
            logger.exception('Google Drive download error')

        return zone_files

    def load_local_files(self, date_str, zone_filter=None):
        """Load Zone CSV files from local cache

        Supports two formats:
        1. Zone{zone}_{date}.csv or Zone{zone}.csv - Combined files with GRIDCODE column
        2. Zone{zone}_{gridcode}.csv - Individual files per point (time series)
        """
        self.stdout.write(f'  📂 Loading from local cache...')

        zone_files = []

        # Pattern for Zone{zone}_{gridcode}.csv (individual point files)
        point_pattern = re.compile(r'Zone(\d+)_(\d+)\.csv', re.IGNORECASE)

        # Patterns for combined files
        combined_patterns = [
            re.compile(rf'Zone(\d+)_{date_str}\.csv', re.IGNORECASE),
            re.compile(rf'Zone(\d+)\.csv', re.IGNORECASE),
        ]

        for file_path in self.cache_dir.glob('Zone*.csv'):
            # First check for individual point files
            point_match = point_pattern.match(file_path.name)
            if point_match:
                zone_num = int(point_match.group(1))
                gridcode = int(point_match.group(2))

                if zone_filter and zone_num != zone_filter:
                    continue

                try:
                    csv_content = file_path.read_text()
                    zone_files.append({
                        'zone': zone_num,
                        'gridcode': gridcode,
                        'filename': file_path.name,
                        'content': csv_content,
                        'format': 'point'  # Mark as individual point file
                    })
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f'    ⚠️  Failed to read {file_path.name}: {e}'
                    ))
                continue

            # Check combined file patterns
            for pattern in combined_patterns:
                match = pattern.match(file_path.name)
                if match:
                    zone_num = int(match.group(1))

                    if zone_filter and zone_num != zone_filter:
                        continue

                    try:
                        csv_content = file_path.read_text()
                        zone_files.append({
                            'zone': zone_num,
                            'filename': file_path.name,
                            'content': csv_content,
                            'format': 'combined'
                        })
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            f'    ⚠️  Failed to read {file_path.name}: {e}'
                        ))
                    break

        if zone_files:
            self.stdout.write(self.style.SUCCESS(
                f'  ✅ Loaded {len(zone_files)} files from cache'
            ))

        return zone_files

    def create_geojson(self, zone_files, control_points, date_obj):
        """Parse CSV and create GeoJSON FeatureCollection

        Handles two formats:
        1. Combined: Files with GRIDCODE column, each row is a point
        2. Point: Individual files per point, each row is a time step
        """
        self.stdout.write(f'  🔄 Merging Zone data with control points...')

        # Parse all CSVs and organize by (zone, gridcode)
        forecast_data = {}  # {(zone, gridcode): [forecast_records]}

        for zone_file in zone_files:
            zone_num = zone_file['zone']
            file_format = zone_file.get('format', 'combined')

            if file_format == 'point':
                # Individual point file: Zone{zone}_{gridcode}.csv
                # Each row is a time step with date as first column
                gridcode = zone_file.get('gridcode')
                key = (zone_num, gridcode)

                if key not in forecast_data:
                    forecast_data[key] = []

                try:
                    lines = zone_file['content'].strip().split('\n')
                    if len(lines) < 2:
                        continue

                    # Parse header (first column is date index, rest are model names)
                    header = lines[0].split(',')
                    model_cols = header[1:]  # Skip empty first column

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

                        forecast_record = {'date': date_str}

                        for i, model_name in enumerate(model_cols):
                            if i + 1 < len(values):
                                value = values[i + 1].strip()
                                if value and value != '':
                                    try:
                                        val = float(value)
                                        # Filter out placeholder values
                                        if val > -1e-20 and val < 1e10:
                                            forecast_record[model_name] = val
                                    except ValueError:
                                        pass

                        forecast_data[key].append(forecast_record)

                except Exception as e:
                    logger.error(f'Error parsing point file {zone_file["filename"]}: {e}')
                    continue

            else:
                # Combined format: GRIDCODE column with each row being a point
                reader = csv.DictReader(StringIO(zone_file['content']))

                for row in reader:
                    try:
                        gridcode = int(row.get('GRIDCODE', 0))
                        key = (zone_num, gridcode)

                        if key not in forecast_data:
                            forecast_data[key] = []

                        # Store all forecast data from row
                        forecast_record = {}
                        for col, value in row.items():
                            forecast_record[col] = value if value else '0'

                        forecast_data[key].append(forecast_record)

                    except Exception as e:
                        logger.error(f'Error parsing row in Zone{zone_num}: {e}')
                        continue

        # Create GeoJSON features
        features = []
        matched = 0

        for key, point in control_points.items():
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
                    'forecasts': forecasts  # Time series array
                }
            }
            features.append(feature)

            if forecasts:
                matched += 1

        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'date': date_obj.strftime('%Y-%m-%d'),
                'total_points': len(features),
                'matched_points': matched,
                'zones_processed': len(zone_files)
            }
        }

        self.stdout.write(self.style.SUCCESS(
            f'  ✅ Created GeoJSON: {len(features)} features ({matched} with data)'
        ))

        return geojson

    def check_exists(self, date_obj):
        """Check if data for this date already exists"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM home_ensemble_forecast_geojson
                    WHERE data_date = %s
                )
            """, [date_obj.date()])
            return cursor.fetchone()[0]

    def save_to_database(self, geojson, date_obj):
        """Save GeoJSON to database"""
        self.stdout.write(f'  💾 Saving to database...')

        try:
            date_str = date_obj.strftime('%Y%m%d')
            feature_count = len(geojson['features'])
            matched_count = sum(1 for f in geojson['features']
                               if f['properties'].get('has_data'))

            with connection.cursor() as cursor:
                # Insert or update
                cursor.execute("""
                    INSERT INTO home_ensemble_forecast_geojson (
                        data_date,
                        date_string,
                        geojson_data,
                        feature_count,
                        matched_count,
                        processed_by,
                        created_at,
                        updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                    ON CONFLICT (data_date)
                    DO UPDATE SET
                        geojson_data = EXCLUDED.geojson_data,
                        feature_count = EXCLUDED.feature_count,
                        matched_count = EXCLUDED.matched_count,
                        processed_by = EXCLUDED.processed_by,
                        updated_at = NOW()
                """, [
                    date_obj.date(),
                    date_str,
                    json.dumps(geojson),
                    feature_count,
                    matched_count,
                    'sync_ensemble_from_ftp'
                ])

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Database error: {e}'))
            logger.exception('Database save error')
            return False
