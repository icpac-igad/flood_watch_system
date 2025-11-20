"""
Django Management Command: Sync Ensemble Forecasts from FTP to Database

Downloads Zone*.csv files from FTP, merges with control point locations,
and saves as GeoJSON to the database.

Usage:
    python manage.py sync_ensemble_from_ftp                 # Download all zones
    python manage.py sync_ensemble_from_ftp --zone 1        # Only Zone 1
    python manage.py sync_ensemble_from_ftp --limit 100     # Limit to 100 files
    python manage.py sync_ensemble_from_ftp --dry-run       # Don't save to DB
"""

from django.core.management.base import BaseCommand
from Impact.models import EnsembleForecastGeoJSON
from ftplib import FTP
from pathlib import Path
from datetime import datetime, timedelta, time
import csv
import json
import os
import re
import tempfile
import shutil
from io import StringIO
from django.utils import timezone


class Command(BaseCommand):
    help = 'Sync ensemble forecasts from FTP to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--zone',
            type=int,
            help='Only download files for specific zone (1-6)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of files to download',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Download and merge but don\'t save to database',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing data for the same date',
        )
        parser.add_argument(
            '--keep-temp',
            action='store_true',
            help='Keep temporary files (don\'t clean up)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Ensemble Forecast FTP → Database Sync'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # FTP configuration
        self.ftp_config = {
            'host': os.getenv('FTP_HOST'),
            'port': int(os.getenv('FTP_PORT', 21)),
            'user': os.getenv('FTP_USER'),
            'password': os.getenv('FTP_PASSWORD'),
            'remote_dir': os.getenv('FTP_REMOTE_DIR', 'output/Combined')
        }

        if not all([self.ftp_config['host'], self.ftp_config['user'], self.ftp_config['password']]):
            self.stdout.write(self.style.ERROR('✗ Missing FTP credentials in environment'))
            return

        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix='ensemble_ftp_'))
        self.stdout.write(f'Temp directory: {self.temp_dir}\n')

        try:
            # Step 1: Load control points from existing data
            control_points = self.load_control_points()
            if not control_points:
                return

            # Step 2: Download files from FTP
            zone_files = self.download_ftp_files(options['zone'], options.get('limit'))
            if not zone_files:
                return

            # Step 3: Parse and merge data
            geojson = self.create_merged_geojson(zone_files, control_points)
            if not geojson:
                return

            # Step 4: Save to database
            if not options['dry_run']:
                self.save_to_database(geojson, force=options.get('force', False))
            else:
                self.stdout.write(self.style.WARNING('\n⊘ DRY RUN - Skipping database save'))

            # Step 5: Cleanup
            if not options['keep_temp']:
                shutil.rmtree(self.temp_dir)
                self.stdout.write(f'\n✓ Cleaned up temp directory')
            else:
                self.stdout.write(f'\n⊘ Temp files kept at: {self.temp_dir}')

            self.stdout.write(self.style.SUCCESS('\n' + '='*60))
            self.stdout.write(self.style.SUCCESS('✓ SYNC COMPLETE'))
            self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            import traceback
            traceback.print_exc()

    def load_control_points(self):
        """Load control points from static ensemble_control_file.geojson"""
        self.stdout.write('STEP 1: Loading control points...')

        try:
            import json
            control_file = '/app/static_data/ensemble_control_file.geojson'

            with open(control_file, 'r') as f:
                data = json.load(f)

            # Extract control points from GeoJSON
            # Key is (Zone, GRIDCODE) tuple since GRIDCODE repeats across zones
            control_points = {}
            for feature in data.get('features', []):
                props = feature['properties']
                zone = props.get('Zone')
                gridcode = props.get('GRIDCODE')
                if zone and gridcode:
                    key = (zone, gridcode)
                    control_points[key] = {
                        'coords': feature['geometry']['coordinates'],
                        'zone': zone,
                        'id': props.get('ID'),
                        'x': props.get('x'),
                        'y': props.get('y'),
                        'admin_name': props.get('admin_name'),
                        'node': props.get('Node'),
                        'gridcode': gridcode,
                    }

            self.stdout.write(self.style.SUCCESS(f'  ✓ Loaded {len(control_points)} control points from {control_file}\n'))
            return control_points

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
            import traceback
            traceback.print_exc()
            return None

    def download_ftp_files(self, zone_filter=None, limit=None):
        """Download Zone*.csv files from FTP server"""
        self.stdout.write('STEP 2: Downloading files from FTP...')

        try:
            # Connect
            self.stdout.write(f'  Connecting to {self.ftp_config["host"]}...')
            ftp = FTP()
            ftp.connect(self.ftp_config['host'], self.ftp_config['port'], timeout=30)
            ftp.login(self.ftp_config['user'], self.ftp_config['password'])
            ftp.set_pasv(True)
            ftp.cwd(self.ftp_config['remote_dir'])
            self.stdout.write(self.style.SUCCESS('  ✓ Connected'))

            # List files
            all_files = ftp.nlst()
            pattern = re.compile(r'Zone(\d+)_(\d+)\.csv', re.IGNORECASE)
            zone_files = []

            for filename in all_files:
                match = pattern.match(filename)
                if match:
                    zone_num = int(match.group(1))
                    file_num = int(match.group(2))

                    # Apply zone filter
                    if zone_filter and zone_num != zone_filter:
                        continue

                    zone_files.append((zone_num, file_num, filename))

            # Apply limit
            if limit:
                zone_files = zone_files[:limit]

            self.stdout.write(f'  Found {len(zone_files)} files to download')

            # Download files
            downloaded = []
            for i, (zone_num, file_num, filename) in enumerate(zone_files, 1):
                if i % 100 == 0:
                    self.stdout.write(f'    Progress: {i}/{len(zone_files)}')

                # Download to memory
                lines = []
                ftp.retrlines(f'RETR {filename}', lines.append)
                csv_content = '\n'.join(lines)

                # Save to temp file
                temp_file = self.temp_dir / filename
                temp_file.write_text(csv_content)

                downloaded.append({
                    'zone': zone_num,
                    'file_num': file_num,
                    'filename': filename,
                    'content': csv_content,
                })

            ftp.quit()
            self.stdout.write(self.style.SUCCESS(f'  ✓ Downloaded {len(downloaded)} files\n'))
            return downloaded

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ FTP error: {e}'))
            return None

    def create_merged_geojson(self, zone_files, control_points):
        """Parse CSV files and create merged GeoJSON"""
        self.stdout.write('STEP 3: Merging CSV data with control points...')

        # Parse all CSV files and group by (Zone, GRIDCODE)
        gridcode_data = {}  # {(zone, gridcode): [{date, floodproof, ...}]}

        for file_info in zone_files:
            zone_num = file_info['zone']
            gridcode = file_info['file_num']  # Zone1_4.csv -> Zone 1, GRIDCODE 4
            key = (zone_num, gridcode)

            reader = csv.DictReader(StringIO(file_info['content']))
            forecasts = []

            for row in reader:
                # First column is date (may be unnamed)
                date_col = row.get('') or list(row.values())[0] if row else None

                if date_col:
                    # Dynamically extract ALL model columns from the CSV
                    # Include all columns, even if value is '0' or empty
                    forecast_record = {'date': date_col}

                    for col, value in row.items():
                        # Skip only the empty column name (date column)
                        # Include all other columns even if value is '0' or empty
                        if col:
                            forecast_record[col] = value if value else '0'

                    forecasts.append(forecast_record)

            if forecasts:
                gridcode_data[key] = forecasts

        self.stdout.write(f'  Parsed {len(gridcode_data)} control points with forecast data')

        # Create GeoJSON features
        features = []
        matched = 0

        for key, forecasts in gridcode_data.items():
            control_point = control_points.get(key)

            if not control_point:
                continue  # Skip if no coordinates found

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': control_point['coords']
                },
                'properties': {
                    'GRIDCODE': control_point['gridcode'],
                    'ID': control_point.get('id'),
                    'Zone': control_point.get('zone'),
                    'x': control_point.get('x'),
                    'y': control_point.get('y'),
                    'admin_name': control_point.get('admin_name'),
                    'has_data': True,
                    'forecasts': forecasts  # Time series array
                }
            }
            features.append(feature)
            matched += 1

        # Add control points without forecast data
        for key, cp in control_points.items():
            if key not in gridcode_data:
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': cp['coords']
                    },
                    'properties': {
                        'GRIDCODE': cp['gridcode'],
                        'ID': cp.get('id'),
                        'Zone': cp.get('zone'),
                        'x': cp.get('x'),
                        'y': cp.get('y'),
                        'admin_name': cp.get('admin_name'),
                        'has_data': False,
                        'forecasts': []
                    }
                }
                features.append(feature)

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created GeoJSON:'))
        self.stdout.write(f'    Total features: {len(features)}')
        self.stdout.write(f'    With forecast data: {matched}')
        self.stdout.write(f'    Without data: {len(features) - matched}\n')

        # Save merged GeoJSON to temp file
        geojson_file = self.temp_dir / 'ensemble_merged.geojson'
        geojson_file.write_text(json.dumps(geojson, indent=2))
        self.stdout.write(f'  Saved to: {geojson_file}\n')

        self.geojson = geojson
        return geojson

    def save_to_database(self, geojson, force=False):
        """Save merged GeoJSON to database"""
        self.stdout.write('STEP 4: Saving to database...')

        try:
            # Extract data date from the first date in forecast data
            # The first date in the forecasts array is the base forecast date
            date_obj = None
            for feature in geojson['features']:
                forecasts = feature['properties'].get('forecasts', [])
                if forecasts and len(forecasts) > 0:
                    # Get the first date from forecasts (base forecast date)
                    first_date_str = forecasts[0].get('date')
                    if first_date_str:
                        try:
                            date_obj = datetime.strptime(first_date_str, '%Y-%m-%d').date()
                            self.stdout.write(f'  📅 Using first forecast date as data date: {date_obj}')
                            break
                        except:
                            pass

            # Fallback to yesterday if no date found in forecasts
            if not date_obj:
                date_obj = (timezone.now() - timedelta(days=1)).date()
                self.stdout.write(self.style.WARNING(f'  ⚠ Could not extract date from forecasts, using yesterday: {date_obj}'))

            date_string = date_obj.strftime('%Y%m%d')

            features_with_data = sum(1 for f in geojson['features'] if f['properties'].get('has_data'))
            features_without_data = len(geojson['features']) - features_with_data

            # Check if date already exists
            existing = EnsembleForecastGeoJSON.objects.filter(date_string=date_string).first()

            if existing and not force:
                self.stdout.write(self.style.WARNING(f'  ⊘ Record for {date_obj} already exists'))
                self.stdout.write(f'     Existing: {existing.features_with_data} features with data')
                self.stdout.write(f'     New data: {features_with_data} features with data')
                self.stdout.write(f'     Use --force to overwrite')
                return
            elif existing and force:
                # Update existing record
                existing.geojson_data = geojson
                existing.feature_count = len(geojson['features'])
                existing.features_with_data = features_with_data
                existing.features_without_data = features_without_data
                existing.processed_by = 'sync_ensemble_from_ftp'
                existing.save()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated existing record for {date_obj} (forced)'))
                return

            # Create new record
            record = EnsembleForecastGeoJSON.objects.create(
                date_string=date_string,
                data_date=date_obj,
                geojson_data=geojson,
                feature_count=len(geojson['features']),
                features_with_data=features_with_data,
                features_without_data=features_without_data,
                processed_by='sync_ensemble_from_ftp',
                file_path=f'ftp_sync/ensemble_{date_string}.geojson'
            )
            created = True

            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created new record for {date_obj}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated existing record for {date_obj}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Database error: {e}'))
