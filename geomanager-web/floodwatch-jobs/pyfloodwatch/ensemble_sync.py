"""Ensemble FTP sync module using curl with parallel downloads"""
import subprocess
import csv
import os
from io import StringIO
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .settings import ENSEMBLE_CONFIG, DATA_DIR, SYNC_DAYS, DB_CONFIG
from .database import ingest_ensemble_geojson, get_db_connection
from .logger_config import setup_logger

logger = setup_logger(__name__, 'ensemble_sync.log')

# Number of parallel downloads (higher = faster but more FTP load)
PARALLEL_DOWNLOADS = 50


class EnsembleSyncer:
    """Syncs Ensemble forecast data from FTP using curl"""

    def __init__(self):
        self.config = ENSEMBLE_CONFIG
        self.cache_dir = DATA_DIR / 'ensemble'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.control_points = {}

    def load_control_points(self):
        """Load control points from database"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT zone, gridcode, x as lon, y as lat, admin_name
                    FROM public.multimodal_control_points
                """)
                rows = cursor.fetchall()

                for row in rows:
                    zone, gridcode, lon, lat, name = row
                    key = f"Zone{zone}_{gridcode}"
                    self.control_points[key] = {
                        'zone': zone,
                        'gridcode': gridcode,
                        'lon': lon,
                        'lat': lat,
                        'name': name
                    }

                logger.info(f"Loaded {len(self.control_points)} control points")
                return True
        except Exception as e:
            logger.error(f"Failed to load control points: {e}")
            return False

    def bulk_download_ftp(self):
        """Bulk download all CSV files from FTP using wget"""
        try:
            # Clear existing cache
            for f in self.cache_dir.glob('*.csv'):
                f.unlink()

            logger.info(f"Starting bulk download from FTP...")

            # Use wget with explicit FTP credentials
            cmd = [
                'wget', '-r', '-l1', '-np', '-nH', '-nd',
                '--ftp-user=' + self.config['username'],
                '--ftp-password=' + self.config['password'],
                '-P', str(self.cache_dir),
                '-A', 'Zone*.csv',
                '--tries=2',
                '--timeout=60',
                f"ftp://{self.config['host']}{self.config['remote_dir']}/"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout

            # Count downloaded files
            downloaded = list(self.cache_dir.glob('Zone*.csv'))
            logger.info(f"Downloaded {len(downloaded)} CSV files")
            return len(downloaded) > 100  # Need substantial files

        except subprocess.TimeoutExpired:
            logger.error("Bulk download timed out after 30 minutes")
            return False
        except Exception as e:
            logger.error(f"Bulk download failed: {e}")
            return False

    def _parallel_download(self, files):
        """Fallback parallel download using curl"""
        logger.info(f"Starting parallel download of {len(files)} files...")

        def download_one(filename):
            local_path = self.cache_dir / filename
            return self.download_file(filename, local_path)

        completed = 0
        with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOADS) as executor:
            futures = {executor.submit(download_one, f): f for f in files}
            for future in as_completed(futures):
                completed += 1
                if completed % 500 == 0:
                    logger.info(f"  Downloaded: {completed}/{len(files)} files")

    def list_ftp_files(self):
        """List files in FTP directory using curl"""
        try:
            ftp_url = f"ftp://{self.config['host']}{self.config['remote_dir']}/"
            cmd = [
                'curl', '-s', '--user',
                f"{self.config['username']}:{self.config['password']}",
                '--connect-timeout', '30',
                '--max-time', '60',
                ftp_url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

            if result.returncode != 0:
                logger.error(f"FTP list failed: {result.stderr}")
                return []

            # Parse file listing
            files = []
            for line in result.stdout.strip().split('\n'):
                if line and not line.startswith('d'):  # Skip directories
                    parts = line.split()
                    if parts:
                        filename = parts[-1]
                        if filename.endswith('.csv') and filename.startswith('Zone'):
                            files.append(filename)

            logger.info(f"Found {len(files)} CSV files on FTP")
            return files

        except Exception as e:
            logger.error(f"Failed to list FTP files: {e}")
            return []

    def download_file(self, filename, local_path, retries=2):
        """Download file using curl with retries"""
        ftp_url = f"ftp://{self.config['host']}{self.config['remote_dir']}/{filename}"

        for attempt in range(retries):
            try:
                cmd = [
                    'curl', '-s', '--ftp-pasv', '--user',
                    f"{self.config['username']}:{self.config['password']}",
                    '--connect-timeout', '15',
                    '--max-time', '30',
                    '-o', str(local_path),
                    ftp_url
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)

                if result.returncode == 0 and local_path.exists() and local_path.stat().st_size > 0:
                    return True

            except:
                pass

            import time
            time.sleep(1)

        return False

    def parse_csv_file(self, filepath):
        """Parse ensemble CSV file"""
        try:
            data = {}
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Get date from row - check for 'Date', 'date', or empty string (no header)
                    date_str = row.get('Date', row.get('date', row.get('', '')))
                    if date_str:
                        if date_str not in data:
                            data[date_str] = {}
                        # Store all model columns
                        for key, value in row.items():
                            if key and key.lower() != 'date':
                                data[date_str][key] = value
            return data
        except Exception as e:
            logger.error(f"Parse error for {filepath}: {e}")
            return {}

    def safe_float(self, val):
        """Parse numeric values safely"""
        if val is None or val == '':
            return None
        try:
            f = float(val)
            # Filter out invalid values (negative tiny numbers used as null)
            if f < -1e-20:
                return None
            return f
        except:
            return None

    def create_geojson_with_all_forecasts(self, all_point_data, all_dates):
        """Create GeoJSON with all forecast dates in the forecasts array"""
        features = []
        matched_count = 0
        point_id = 1

        # Sort dates chronologically
        sorted_dates = sorted(all_dates)

        for key, point_info in self.control_points.items():
            point_data = all_point_data.get(key, {})

            # Build forecasts array with ALL dates
            forecasts = []
            for date_str in sorted_dates:
                date_data = point_data.get(date_str, {})
                if date_data:
                    forecast_entry = {
                        'date': date_str,
                        'GeoSFM': self.safe_float(date_data.get('GeoSFM')),
                        'Floodproof': self.safe_float(date_data.get('Floodproof')),
                        'Mike_Hydro_RFE': self.safe_float(date_data.get('Mike_Hydro_RFE')),
                        'Mike_Hydro_CHIRP': self.safe_float(date_data.get('Mike_Hydro_CHIRP')),
                        'Mike_Hydro_IMERG': self.safe_float(date_data.get('Mike_Hydro_IMERG')),
                        'daily_avg': self.safe_float(date_data.get('daily_avg')),
                        'daily_max': self.safe_float(date_data.get('daily_max')),
                        'daily_min': self.safe_float(date_data.get('daily_min')),
                    }
                    forecasts.append(forecast_entry)

            has_data = len(forecasts) > 0

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(point_info['lon']), float(point_info['lat'])]
                },
                'properties': {
                    'ID': point_id,
                    'point_id': point_id,
                    'x': float(point_info['lon']),
                    'y': float(point_info['lat']),
                    'Zone': point_info['zone'],
                    'zone': point_info['zone'],
                    'GRIDCODE': point_info['gridcode'],
                    'gridcode': point_info['gridcode'],
                    'has_data': has_data,
                    'admin_name': point_info['name'] or str(point_info['zone']),
                    'is_node': True,
                    'forecasts': forecasts
                }
            }
            features.append(feature)
            if has_data:
                matched_count += 1
            point_id += 1

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        return geojson, matched_count

    def sync(self):
        """Main sync function"""
        logger.info("=" * 70)
        logger.info("Ensemble FTP Sync Started")
        logger.info("=" * 70)

        stats = {'files': 0, 'downloaded': 0, 'ingested': False, 'failed': 0}

        try:
            # Load control points
            if not self.load_control_points():
                logger.error("Cannot proceed without control points")
                return False

            # Clear cache and download fresh
            for f in self.cache_dir.glob('*.csv'):
                f.unlink()

            # List files on FTP
            files = self.list_ftp_files()
            if not files:
                logger.error("No files found on FTP")
                return False

            # Parallel download with 10 workers
            logger.info(f"Downloading {len(files)} files with 10 parallel connections...")
            downloaded = [0]
            failed = [0]
            completed = [0]

            def download_one(filename):
                local_path = self.cache_dir / filename
                success = self.download_file(filename, local_path)
                completed[0] += 1
                if success:
                    downloaded[0] += 1
                else:
                    failed[0] += 1
                if completed[0] % 100 == 0:
                    logger.info(f"  {completed[0]}/{len(files)} - success: {downloaded[0]}, failed: {failed[0]}")
                return success

            with ThreadPoolExecutor(max_workers=10) as executor:
                list(executor.map(download_one, files))

            logger.info(f"Download complete: {downloaded[0]} success, {failed[0]} failed")

            # Process downloaded files
            csv_files = list(self.cache_dir.glob('Zone*.csv'))
            stats['files'] = len(csv_files)
            logger.info(f"Processing {len(csv_files)} downloaded CSV files...")

            all_point_data = {}
            all_dates = set()

            for i, filepath in enumerate(csv_files):
                try:
                    filename = filepath.name
                    parts = filename.replace('.csv', '').split('_')
                    zone = int(parts[0].replace('Zone', ''))
                    gridcode = int(parts[1])
                    key = f"Zone{zone}_{gridcode}"

                    point_data = self.parse_csv_file(filepath)
                    if point_data:
                        all_point_data[key] = point_data
                        all_dates.update(point_data.keys())
                        stats['downloaded'] += 1
                except Exception as e:
                    continue

                if (i + 1) % 500 == 0:
                    logger.info(f"  Parsed: {i + 1}/{len(csv_files)} files")

            logger.info(f"Processed {len(all_point_data)} points with data")
            logger.info(f"Found {len(all_dates)} unique forecast dates: {sorted(all_dates)}")

            if not all_dates:
                logger.error("No forecast dates found in CSV files")
                return False

            # Create ONE GeoJSON with ALL forecasts in the array
            # Use today's date as the data_date (when the forecast was generated)
            data_date = datetime.now().date()
            date_string = data_date.strftime('%Y%m%d')

            # Create GeoJSON with all forecasts
            geojson, matched = self.create_geojson_with_all_forecasts(all_point_data, all_dates)
            feature_count = len(geojson['features'])

            logger.info(f"Created GeoJSON: {matched}/{feature_count} points with forecast data")
            logger.info(f"Forecast dates range: {min(all_dates)} to {max(all_dates)}")

            # Ingest as a single record for today's date
            if ingest_ensemble_geojson(data_date, date_string, geojson, feature_count, matched):
                stats['ingested'] = True
                logger.info(f"✓ Successfully ingested multimodal data for {data_date}")
            else:
                stats['failed'] += 1

            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("Ensemble Sync Complete")
            logger.info(f"Files: {stats['files']} | Downloaded: {stats['downloaded']} | "
                       f"Ingested: {stats['ingested']} | Failed: {stats['failed']}")
            logger.info("=" * 70)

            return stats['ingested']

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


def run_ensemble_sync():
    """Entry point for Ensemble sync"""
    syncer = EnsembleSyncer()
    return syncer.sync()


if __name__ == "__main__":
    run_ensemble_sync()
