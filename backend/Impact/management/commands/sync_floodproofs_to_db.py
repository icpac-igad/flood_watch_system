"""
Management command to sync FloodProofs (merged deterministic forecast) data from SFTP to database.

This command:
1. Connects to SFTP server
2. Downloads merged_data_*.geojson files
3. Parses the GeoJSON data
4. Saves to MergedDeterministicGeoJSON model

Usage:
    python manage.py sync_floodproofs_to_db
    python manage.py sync_floodproofs_to_db --date 2025-10-22
    python manage.py sync_floodproofs_to_db --days 7
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from Impact.models import MergedDeterministicGeoJSON
import paramiko
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync FloodProofs merged deterministic forecast data from SFTP to database'

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

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting FloodProofs SFTP to DB sync...'))

        # Get SFTP credentials from environment
        SFTP_HOST = os.environ.get('SFTP_HOST', '197.254.113.173')
        SFTP_PORT = int(os.environ.get('SFTP_PORT', 22))
        SFTP_USERNAME = os.environ.get('SFTP_USERNAME', 'floodproofs')
        # Hardcoded password as fallback (python-decouple has issues with # in .env)
        SFTP_PASSWORD = os.environ.get('SFTP_PASSWORD') or 'IcpaC#254'
        REMOTE_DIR = "/home/floodproofs/merged_forecasts"

        use_sftp = not options['local'] and all([SFTP_HOST, SFTP_USERNAME, SFTP_PASSWORD])

        if not use_sftp:
            self.stdout.write(self.style.WARNING('SFTP credentials not found or --local flag used. Using local filesystem...'))

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
                self.stdout.write(self.style.WARNING('Falling back to local filesystem...'))
                use_sftp = False

        try:
            for date_obj in dates_to_sync:
                date_str = date_obj.strftime('%Y%m%d')
                date_iso = date_obj.strftime('%Y-%m-%d')
                filename = f"merged_data_{date_str}.geojson"

                # Check if already exists in database
                if not options['force']:
                    if MergedDeterministicGeoJSON.objects.filter(data_date=date_obj.date()).exists():
                        self.stdout.write(f'  Skipping {date_iso}: Already in database')
                        skipped_count += 1
                        continue

                # Download/load the file
                geojson_data = None

                if use_sftp:
                    try:
                        remote_file_path = f"{REMOTE_DIR}/{filename}"

                        # Download to temporary location
                        temp_path = f"/tmp/{filename}"
                        self.stdout.write(f'  Downloading {filename} from SFTP...')
                        sftp.get(remote_file_path, temp_path)

                        # Read the file
                        with open(temp_path, 'r') as f:
                            geojson_data = json.load(f)

                        # Clean up temp file
                        os.remove(temp_path)

                    except FileNotFoundError:
                        self.stdout.write(self.style.WARNING(f'  File not found on SFTP: {filename}'))
                        error_count += 1
                        continue
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Error downloading {filename}: {e}'))
                        error_count += 1
                        continue
                else:
                    # Local filesystem - use data/merged_forecasts relative to project root
                    # Get project root (5 levels up from this file: commands/sync_floodproofs_to_db.py)
                    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
                    LOCAL_DIR = PROJECT_ROOT / "data" / "merged_forecasts"

                    if not LOCAL_DIR.exists():
                        # Fallback to old location
                        LOCAL_DIR = Path("/home/floodproofs/merged_forecasts")

                    local_file_path = LOCAL_DIR / filename

                    if not local_file_path.exists():
                        self.stdout.write(self.style.WARNING(f'  File not found locally: {filename}'))
                        error_count += 1
                        continue

                    try:
                        with open(local_file_path, 'r') as f:
                            geojson_data = json.load(f)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Error reading {filename}: {e}'))
                        error_count += 1
                        continue

                # Save to database
                if geojson_data:
                    try:
                        feature_count = len(geojson_data.get('features', []))

                        # Create or update record
                        obj, created = MergedDeterministicGeoJSON.objects.update_or_create(
                            data_date=date_obj.date(),
                            defaults={
                                'date_string': date_str,
                                'geojson_data': geojson_data,
                                'feature_count': feature_count,
                                'file_count': 1,  # Single merged file
                                'file_path': filename,
                                'processed_by': 'sync_floodproofs_to_db',
                            }
                        )

                        action = 'Created' if created else 'Updated'
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ {action} {date_iso}: {feature_count} features'
                        ))
                        synced_count += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Error saving {date_iso} to database: {e}'))
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
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'Sync completed!'))
        self.stdout.write(f'  Synced: {synced_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Errors: {error_count}')
        self.stdout.write(self.style.SUCCESS('='*50))
