"""
Management command to sync GeoSFM Ensemble forecast data from SFTP to database.

This command:
1. Connects to SFTP server (41.215.21.156)
2. Downloads Zone*.csv files from /ftproot/output/Combined
3. Merges the CSV data with EnsembleControlPoint geometries
4. Creates GeoJSON with forecast values
5. Saves to GeoSFMForecastGeoJSON model

Usage:
    python manage.py sync_ensemble_to_db
    python manage.py sync_ensemble_to_db --date 2025-10-22
    python manage.py sync_ensemble_to_db --days 7
    python manage.py sync_ensemble_to_db --local  # Use local files instead of SFTP
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from Impact.models import GeoSFMForecastGeoJSON, EnsembleControlPoint
from django.contrib.gis.geos import Point
import paramiko
import os
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
from io import StringIO
import re

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync GeoSFM ensemble forecast data from SFTP to database'

    def add_arguments(self, parser):
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
            '--force',
            action='store_true',
            help='Force re-download even if data already exists in database',
        )
        parser.add_argument(
            '--local',
            action='store_true',
            help='Use local filesystem instead of SFTP',
        )
        parser.add_argument(
            '--cache-dir',
            type=str,
            default='/app/ensemble_cache',
            help='Local directory to cache downloaded files',
        )

    def parse_zone_csv(self, csv_content: str, zone_number: int):
        """Parse a Zone CSV file and return a dict mapping GRIDCODE to forecast values.

        Expected CSV format:
        GRIDCODE,DATE,RIVERDEPTH,STREAMFLOW
        42,20251022,1.5,25.3
        """
        data = {}

        try:
            reader = csv.DictReader(StringIO(csv_content))
            for row in reader:
                gridcode = int(row['GRIDCODE'])
                date_str = row['DATE']  # YYYYMMDD format
                riverdepth = float(row.get('RIVERDEPTH', 0))
                streamflow = float(row.get('STREAMFLOW', 0))

                # Store by GRIDCODE
                data[gridcode] = {
                    'date': date_str,
                    'riverdepth': riverdepth,
                    'streamflow': streamflow,
                    'zone': zone_number
                }
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error parsing Zone{zone_number} CSV: {e}'))
            logger.error(f'Error parsing Zone{zone_number} CSV: {e}')

        return data

    def merge_ensemble_data(self, date_obj):
        """Merge ensemble forecast data with control points to create GeoJSON.

        Returns:
            tuple: (geojson_data, matched_count, zones_processed)
        """
        # Load all control points
        control_points = EnsembleControlPoint.objects.all()

        if not control_points.exists():
            self.stdout.write(self.style.ERROR('  No EnsembleControlPoint records found in database!'))
            self.stdout.write(self.style.WARNING('  Run "python manage.py load_all_static_data" first'))
            return None, 0, 0

        # Build GeoJSON features
        features = []
        matched_count = 0

        # Get ensemble data by zone (this would be populated from CSV files)
        # For now, create placeholder structure
        for point in control_points:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [point.x, point.y]
                },
                'properties': {
                    'point_id': point.point_id,
                    'gridcode': point.gridcode,
                    'admin_name': point.admin_name or 'Unknown',
                    'zone': point.zone,
                    'riverdepth': None,  # Will be populated from CSV
                    'streamflow': None,  # Will be populated from CSV
                    'date': date_obj.strftime('%Y%m%d')
                }
            }
            features.append(feature)

        geojson_data = {
            'type': 'FeatureCollection',
            'features': features
        }

        return geojson_data, matched_count, 0  # zones_processed will be updated later

    def download_zone_files(self, sftp, remote_dir, local_cache_dir, date_str):
        """Download all Zone*.csv files for a specific date from SFTP.

        Returns:
            list: List of tuples (zone_number, csv_content)
        """
        zone_files = []

        try:
            # List files in the Combined directory
            files = sftp.listdir(remote_dir)

            # Filter for Zone files with the date
            pattern = re.compile(rf'Zone(\d+)_{date_str}\.csv', re.IGNORECASE)

            for filename in files:
                match = pattern.match(filename)
                if match:
                    zone_number = int(match.group(1))
                    remote_path = f"{remote_dir}/{filename}"

                    try:
                        # Download to memory
                        self.stdout.write(f'    Downloading {filename}...')
                        with sftp.file(remote_path, 'r') as remote_file:
                            csv_content = remote_file.read().decode('utf-8')

                        # Optionally cache to local filesystem
                        if local_cache_dir:
                            local_file = Path(local_cache_dir) / filename
                            local_file.parent.mkdir(parents=True, exist_ok=True)
                            local_file.write_text(csv_content)

                        zone_files.append((zone_number, csv_content))

                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'    Failed to download {filename}: {e}'))
                        logger.error(f'Failed to download {filename}: {e}')

            if not zone_files:
                self.stdout.write(self.style.WARNING(f'  No Zone CSV files found for date {date_str}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Downloaded {len(zone_files)} Zone files'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error listing/downloading Zone files: {e}'))
            logger.error(f'Error listing/downloading Zone files: {e}')

        return zone_files

    def load_local_zone_files(self, local_cache_dir, date_str):
        """Load Zone CSV files from local cache directory.

        Returns:
            list: List of tuples (zone_number, csv_content)
        """
        zone_files = []
        cache_path = Path(local_cache_dir)

        if not cache_path.exists():
            self.stdout.write(self.style.WARNING(f'  Cache directory not found: {local_cache_dir}'))
            return zone_files

        # Pattern: Zone1_20251022.csv
        pattern = re.compile(rf'Zone(\d+)_{date_str}\.csv', re.IGNORECASE)

        for file_path in cache_path.glob('Zone*.csv'):
            match = pattern.match(file_path.name)
            if match:
                zone_number = int(match.group(1))
                try:
                    csv_content = file_path.read_text()
                    zone_files.append((zone_number, csv_content))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    Failed to read {file_path.name}: {e}'))

        if zone_files:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Loaded {len(zone_files)} Zone files from cache'))
        else:
            self.stdout.write(self.style.WARNING(f'  No Zone CSV files found in cache for date {date_str}'))

        return zone_files

    def merge_zone_data_with_points(self, zone_files, date_obj):
        """Merge Zone CSV data with EnsembleControlPoint geometries to create GeoJSON.

        Args:
            zone_files: List of tuples (zone_number, csv_content)
            date_obj: datetime object for the forecast date

        Returns:
            tuple: (geojson_data, matched_count, zones_processed)
        """
        # Parse all zone CSVs into a single dict: GRIDCODE -> forecast_data
        all_forecast_data = {}
        zones_processed = 0

        for zone_number, csv_content in zone_files:
            zone_data = self.parse_zone_csv(csv_content, zone_number)
            all_forecast_data.update(zone_data)
            zones_processed += 1

        # Load all control points
        control_points = EnsembleControlPoint.objects.all()

        if not control_points.exists():
            self.stdout.write(self.style.ERROR('  No EnsembleControlPoint records found in database!'))
            self.stdout.write(self.style.WARNING('  Run "python manage.py load_all_static_data" first'))
            return None, 0, 0

        # Build GeoJSON features by matching control points with forecast data
        features = []
        matched_count = 0

        for point in control_points:
            forecast_data = all_forecast_data.get(point.gridcode)

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [point.x, point.y]
                },
                'properties': {
                    'point_id': point.point_id,
                    'gridcode': point.gridcode,
                    'admin_name': point.admin_name or 'Unknown',
                    'zone': point.zone,
                    'riverdepth': forecast_data['riverdepth'] if forecast_data else None,
                    'streamflow': forecast_data['streamflow'] if forecast_data else None,
                    'date': date_obj.strftime('%Y%m%d'),
                    'has_data': forecast_data is not None
                }
            }

            if forecast_data:
                matched_count += 1

            features.append(feature)

        geojson_data = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'date': date_obj.strftime('%Y-%m-%d'),
                'total_points': len(features),
                'matched_points': matched_count,
                'zones_processed': zones_processed
            }
        }

        return geojson_data, matched_count, zones_processed

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting GeoSFM Ensemble SFTP to DB sync...'))

        # Get SFTP credentials from environment
        SFTP_HOST = os.environ.get('ENSEMBLE_SFTP_HOST', '41.215.21.156')
        SFTP_PORT = int(os.environ.get('ENSEMBLE_SFTP_PORT', 22))
        SFTP_USERNAME = os.environ.get('ENSEMBLE_SFTP_USERNAME', 'geosfm')
        SFTP_PASSWORD = os.environ.get('ENSEMBLE_SFTP_PASSWORD', 'icpac#254')
        REMOTE_DIR = os.environ.get('ENSEMBLE_REMOTE_PATH', '/ftproot/output/Combined')

        # Local cache directory
        local_cache_dir = options['cache_dir']

        use_sftp = not options['local'] and all([SFTP_HOST, SFTP_USERNAME, SFTP_PASSWORD])

        if not use_sftp:
            self.stdout.write(self.style.WARNING('SFTP credentials not found or --local flag used. Using local cache...'))

        # Determine which dates to sync
        if options['date']:
            # Sync specific date
            try:
                date_obj = datetime.strptime(options['date'], '%Y-%m-%d')
                dates_to_sync = [date_obj]
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Invalid date format: {options["date"]}. Use YYYY-MM-DD'))
                return
        else:
            # Sync recent days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=options['days'])
            dates_to_sync = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]

        self.stdout.write(f'Will attempt to sync {len(dates_to_sync)} dates')

        synced_count = 0
        skipped_count = 0
        error_count = 0

        # Connect to SFTP if using remote
        ssh = None
        sftp = None
        if use_sftp:
            try:
                self.stdout.write(f'Connecting to SFTP server {SFTP_HOST}:{SFTP_PORT}...')
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USERNAME,
                           password=SFTP_PASSWORD, timeout=30)
                sftp = ssh.open_sftp()
                sftp.get_channel().settimeout(30)
                self.stdout.write(self.style.SUCCESS('✓ Connected to SFTP server'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to connect to SFTP: {e}'))
                self.stdout.write(self.style.WARNING('Falling back to local cache...'))
                use_sftp = False

        try:
            for date_obj in dates_to_sync:
                date_str = date_obj.strftime('%Y%m%d')  # YYYYMMDD for Zone files
                date_iso = date_obj.strftime('%Y-%m-%d')

                # Check if already exists in database
                if not options['force']:
                    if GeoSFMForecastGeoJSON.objects.filter(data_date=date_obj.date()).exists():
                        self.stdout.write(f'  Skipping {date_iso}: Already in database')
                        skipped_count += 1
                        continue

                self.stdout.write(f'Processing {date_iso}...')

                # Download/load Zone CSV files
                zone_files = []

                if use_sftp:
                    zone_files = self.download_zone_files(sftp, REMOTE_DIR, local_cache_dir, date_str)
                else:
                    zone_files = self.load_local_zone_files(local_cache_dir, date_str)

                if not zone_files:
                    self.stdout.write(self.style.WARNING(f'  No Zone files found for {date_iso}'))
                    error_count += 1
                    continue

                # Merge Zone data with control points to create GeoJSON
                geojson_data, matched_count, zones_processed = self.merge_zone_data_with_points(zone_files, date_obj)

                if not geojson_data:
                    self.stdout.write(self.style.ERROR(f'  Failed to merge data for {date_iso}'))
                    error_count += 1
                    continue

                # Save to database
                try:
                    feature_count = len(geojson_data.get('features', []))

                    # Calculate statistics
                    riverdepth_values = [f['properties']['riverdepth'] for f in geojson_data['features']
                                        if f['properties'].get('riverdepth') is not None]
                    streamflow_values = [f['properties']['streamflow'] for f in geojson_data['features']
                                        if f['properties'].get('streamflow') is not None]

                    # Create or update record
                    obj, created = GeoSFMForecastGeoJSON.objects.update_or_create(
                        data_date=date_obj.date(),
                        defaults={
                            'date_string': date_str,
                            'geojson_data': geojson_data,
                            'feature_count': feature_count,
                            'matched_count': matched_count,
                            'zones_processed': zones_processed,
                            'riverdepth_min': min(riverdepth_values) if riverdepth_values else None,
                            'riverdepth_max': max(riverdepth_values) if riverdepth_values else None,
                            'streamflow_min': min(streamflow_values) if streamflow_values else None,
                            'streamflow_max': max(streamflow_values) if streamflow_values else None,
                            'processed_by': 'sync_ensemble_to_db',
                        }
                    )

                    action = 'Created' if created else 'Updated'
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ {action} {date_iso}: {matched_count}/{feature_count} matched points, {zones_processed} zones'
                    ))
                    synced_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error saving {date_iso} to database: {e}'))
                    logger.exception(f'Error saving {date_iso} to database')
                    error_count += 1

        finally:
            # Clean up SFTP connection
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Sync Complete!'))
        self.stdout.write(f'  Synced: {synced_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Errors: {error_count}')
        self.stdout.write(self.style.SUCCESS('='*60))
