#!/usr/bin/env python3
"""
Test Script: FTP → Merge → DB Pipeline for Ensemble Forecasts

This script tests the complete workflow:
1. Download Zone*.csv files from FTP for a specific date
2. Load control points from database
3. Merge CSV data with control point locations
4. Create merged GeoJSON in temp folder
5. Save to database (impact_ensemble_forecast_geojson table)
6. Clean up temp files

Usage:
    python scripts/test_ensemble_ftp_sync.py                    # Use today's date
    python scripts/test_ensemble_ftp_sync.py --date 2025-11-19  # Specific date
    python scripts/test_ensemble_ftp_sync.py --dry-run          # Don't save to DB
"""

import os
import sys
import json
import csv
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from ftplib import FTP
from io import StringIO
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 8091)),
    'database': os.getenv('DB_NAME', 'floodwatch'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD')
}

# FTP configuration
FTP_CONFIG = {
    'host': os.getenv('FTP_HOST'),
    'port': int(os.getenv('FTP_PORT', 21)),
    'user': os.getenv('FTP_USER'),
    'password': os.getenv('FTP_PASSWORD'),
    'remote_dir': os.getenv('FTP_REMOTE_DIR', 'output/Combined')
}


class EnsembleFTPSync:
    def __init__(self, date_str, dry_run=False):
        self.date_str = date_str  # YYYYMMDD format
        self.date_obj = datetime.strptime(date_str, '%Y%m%d').date()
        self.dry_run = dry_run
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f'ensemble_{date_str}_'))
        self.control_points = {}
        self.zone_data = {}

        print(f"\n{'='*60}")
        print(f"Ensemble Forecast FTP → DB Sync Test")
        print(f"{'='*60}")
        print(f"Date: {self.date_obj} ({self.date_str})")
        print(f"Temp dir: {self.temp_dir}")
        print(f"Dry run: {self.dry_run}")
        print(f"{'='*60}\n")

    def step_1_load_control_points(self):
        """Step 1: Load control points from database"""
        print("STEP 1: Loading control points from database...")

        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if table exists (may have different names)
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema='pgstac'
                AND table_name LIKE '%ensemble%control%'
            """)

            table = cursor.fetchone()

            if not table:
                # Try to extract from existing forecast data
                print("  No control point table found, extracting from forecast data...")
                cursor.execute("""
                    SELECT geojson_data
                    FROM pgstac.impact_ensemble_forecast_geojson
                    ORDER BY data_date DESC
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if row:
                    geojson = row['geojson_data']
                    for feature in geojson.get('features', []):
                        props = feature['properties']
                        gridcode = props.get('GRIDCODE')
                        if gridcode:
                            self.control_points[gridcode] = {
                                'x': props.get('x'),
                                'y': props.get('y'),
                                'zone': props.get('Zone'),
                                'id': props.get('ID'),
                                'coords': feature['geometry']['coordinates']
                            }

                    print(f"  ✓ Extracted {len(self.control_points)} control points from existing data")
                else:
                    print("  ✗ No control point data found!")
                    return False
            else:
                # Load from dedicated table
                table_name = table['table_name']
                cursor.execute(f"""
                    SELECT gridcode, x, y, zone, point_id
                    FROM pgstac."{table_name}"
                """)

                for row in cursor.fetchall():
                    self.control_points[row['gridcode']] = {
                        'x': row['x'],
                        'y': row['y'],
                        'zone': row['zone'],
                        'id': row['point_id'],
                        'coords': [row['x'], row['y']]
                    }

                print(f"  ✓ Loaded {len(self.control_points)} control points from {table_name}")

            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"  ✗ Database error: {e}")
            return False

    def step_2_download_ftp_files(self):
        """Step 2: Download Zone*.csv files from FTP"""
        print("\nSTEP 2: Downloading Zone*.csv files from FTP...")

        if not all([FTP_CONFIG['host'], FTP_CONFIG['user'], FTP_CONFIG['password']]):
            print("  ✗ Missing FTP credentials in .env file")
            return False

        try:
            # Connect to FTP
            print(f"  Connecting to {FTP_CONFIG['host']}:{FTP_CONFIG['port']}...")
            ftp = FTP()
            ftp.connect(FTP_CONFIG['host'], FTP_CONFIG['port'], timeout=30)
            ftp.login(FTP_CONFIG['user'], FTP_CONFIG['password'])
            ftp.set_pasv(True)
            ftp.cwd(FTP_CONFIG['remote_dir'])
            print(f"  ✓ Connected to FTP")

            # List files matching Zone*_{date}.csv pattern
            all_files = ftp.nlst()
            pattern = re.compile(rf'Zone(\d+)_{self.date_str}\.csv', re.IGNORECASE)
            zone_files = [f for f in all_files if pattern.match(f)]

            if not zone_files:
                print(f"  ⊘ No Zone*.csv files found for date {self.date_str}")
                print(f"  Available files: {all_files[:10]}...")
                ftp.quit()
                return False

            print(f"  Found {len(zone_files)} zone files")

            # Download each file
            for filename in zone_files:
                match = pattern.match(filename)
                zone_num = int(match.group(1))

                # Download to memory
                csv_lines = []
                ftp.retrlines(f'RETR {filename}', csv_lines.append)
                csv_content = '\n'.join(csv_lines)

                # Save to temp file
                temp_file = self.temp_dir / filename
                temp_file.write_text(csv_content)

                # Parse CSV
                reader = csv.DictReader(StringIO(csv_content))
                self.zone_data[zone_num] = {}

                for row in reader:
                    try:
                        gridcode = int(row['GRIDCODE'])
                        self.zone_data[zone_num][gridcode] = {
                            'riverdepth': float(row.get('RIVERDEPTH', 0) or 0),
                            'streamflow': float(row.get('STREAMFLOW', 0) or 0),
                        }
                    except (ValueError, KeyError):
                        continue

                print(f"    Zone {zone_num}: {len(self.zone_data[zone_num])} points (saved to {filename})")

            ftp.quit()
            print(f"  ✓ Downloaded {len(zone_files)} files to {self.temp_dir}")
            return True

        except Exception as e:
            print(f"  ✗ FTP error: {e}")
            return False

    def step_3_merge_and_create_geojson(self):
        """Step 3: Merge CSV data with control points and create GeoJSON"""
        print("\nSTEP 3: Merging CSV data with control points...")

        # Flatten zone data
        all_forecasts = {}
        for zone_num, gridcodes in self.zone_data.items():
            for gridcode, values in gridcodes.items():
                all_forecasts[gridcode] = values

        print(f"  Total forecast points: {len(all_forecasts)}")

        # Create GeoJSON features
        features = []
        matched = 0
        missing_coords = 0

        for gridcode, forecast in all_forecasts.items():
            control_point = self.control_points.get(gridcode)

            if not control_point:
                missing_coords += 1
                continue

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': control_point['coords']
                },
                'properties': {
                    'GRIDCODE': gridcode,
                    'ID': control_point.get('id'),
                    'Zone': control_point.get('zone'),
                    'x': control_point['x'],
                    'y': control_point['y'],
                    'date': self.date_str,
                    'riverdepth': forecast['riverdepth'],
                    'streamflow': forecast['streamflow'],
                    'has_data': True
                }
            }
            features.append(feature)
            matched += 1

        # Add control points without forecast data
        for gridcode, control_point in self.control_points.items():
            if gridcode not in all_forecasts:
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': control_point['coords']
                    },
                    'properties': {
                        'GRIDCODE': gridcode,
                        'ID': control_point.get('id'),
                        'Zone': control_point.get('zone'),
                        'x': control_point['x'],
                        'y': control_point['y'],
                        'date': self.date_str,
                        'riverdepth': None,
                        'streamflow': None,
                        'has_data': False
                    }
                }
                features.append(feature)

        # Create GeoJSON
        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'date': self.date_obj.strftime('%Y-%m-%d'),
                'total_points': len(features),
                'points_with_data': matched,
                'points_without_data': len(features) - matched,
            }
        }

        # Save to temp file
        geojson_file = self.temp_dir / f'ensemble_merged_{self.date_str}.geojson'
        geojson_file.write_text(json.dumps(geojson, indent=2))

        print(f"  ✓ Created GeoJSON:")
        print(f"    Total features: {len(features)}")
        print(f"    With forecast data: {matched}")
        print(f"    Without data: {len(features) - matched}")
        print(f"    Missing coordinates: {missing_coords}")
        print(f"    Saved to: {geojson_file}")

        self.geojson = geojson
        self.geojson_file = geojson_file
        return True

    def step_4_save_to_database(self):
        """Step 4: Save merged GeoJSON to database"""
        print("\nSTEP 4: Saving to database...")

        if self.dry_run:
            print("  ⊘ DRY RUN - Skipping database save")
            return True

        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # Check if record exists
            cursor.execute("""
                SELECT id FROM pgstac.impact_ensemble_forecast_geojson
                WHERE date_string = %s
            """, (self.date_str,))

            exists = cursor.fetchone()

            features_with_data = sum(1 for f in self.geojson['features'] if f['properties'].get('has_data'))
            features_without_data = len(self.geojson['features']) - features_with_data

            if exists:
                print(f"  Updating existing record for {self.date_str}...")
                cursor.execute("""
                    UPDATE pgstac.impact_ensemble_forecast_geojson
                    SET geojson_data = %s,
                        feature_count = %s,
                        features_with_data = %s,
                        features_without_data = %s,
                        updated_at = NOW(),
                        processed_by = %s
                    WHERE date_string = %s
                """, (
                    json.dumps(self.geojson),
                    len(self.geojson['features']),
                    features_with_data,
                    features_without_data,
                    'test_ensemble_ftp_sync',
                    self.date_str
                ))
            else:
                print(f"  Inserting new record for {self.date_str}...")
                cursor.execute("""
                    INSERT INTO pgstac.impact_ensemble_forecast_geojson
                    (data_date, date_string, geojson_data, feature_count,
                     features_with_data, features_without_data, processed_by, file_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.date_obj,
                    self.date_str,
                    json.dumps(self.geojson),
                    len(self.geojson['features']),
                    features_with_data,
                    features_without_data,
                    'test_ensemble_ftp_sync',
                    f'temp/ensemble_merged_{self.date_str}.geojson'
                ))

            conn.commit()
            cursor.close()
            conn.close()

            print(f"  ✓ Saved to database")
            return True

        except Exception as e:
            print(f"  ✗ Database error: {e}")
            return False

    def step_5_cleanup(self):
        """Step 5: Clean up temp files"""
        print("\nSTEP 5: Cleaning up temp files...")

        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            print(f"  ✓ Deleted {self.temp_dir}")
        except Exception as e:
            print(f"  ⊘ Failed to delete temp dir: {e}")

    def run(self):
        """Run the complete workflow"""
        success = True

        success = success and self.step_1_load_control_points()
        if not success:
            return False

        success = success and self.step_2_download_ftp_files()
        if not success:
            return False

        success = success and self.step_3_merge_and_create_geojson()
        if not success:
            return False

        success = success and self.step_4_save_to_database()

        self.step_5_cleanup()

        print(f"\n{'='*60}")
        if success:
            print("✓ SYNC COMPLETE")
            print(f"Date: {self.date_obj}")
            print(f"Features: {len(self.geojson['features'])}")
            print(f"With data: {self.geojson['properties']['points_with_data']}")
            print(f"Without data: {self.geojson['properties']['points_without_data']}")
        else:
            print("✗ SYNC FAILED")
        print(f"{'='*60}\n")

        return success


def main():
    parser = argparse.ArgumentParser(description='Test FTP → Merge → DB pipeline')
    parser.add_argument('--date', type=str, help='Date to sync (YYYY-MM-DD format)')
    parser.add_argument('--dry-run', action='store_true', help="Don't save to database")
    args = parser.parse_args()

    # Determine date
    if args.date:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        date_obj = datetime.now().date()

    date_str = date_obj.strftime('%Y%m%d')

    # Run sync
    sync = EnsembleFTPSync(date_str, dry_run=args.dry_run)
    success = sync.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
