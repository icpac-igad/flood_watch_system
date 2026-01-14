"""Ensemble FTP sync module"""
from ftplib import FTP
import csv
from io import StringIO
from datetime import datetime, timedelta
from pathlib import Path
from .settings import ENSEMBLE_CONFIG, DATA_DIR, SYNC_DAYS
from .database import ingest_ensemble_geojson
from .logger_config import setup_logger

logger = setup_logger(__name__, 'ensemble_sync.log')


class EnsembleSyncer:
    """Syncs Ensemble forecast data from FTP"""

    def __init__(self):
        self.config = ENSEMBLE_CONFIG
        self.cache_dir = DATA_DIR / 'ensemble'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def connect_ftp(self):
        """Connect to FTP server"""
        try:
            logger.info(f"Connecting to FTP {self.config['host']}:{self.config['port']}")
            ftp = FTP()
            ftp.connect(self.config['host'], self.config['port'], timeout=30)
            ftp.login(self.config['username'], self.config['password'])
            ftp.set_pasv(True)
            logger.info("✓ FTP connected")
            return ftp
        except Exception as e:
            logger.error(f"✗ FTP connection failed: {e}")
            raise

    def get_dates_to_sync(self, days=SYNC_DAYS):
        """Generate list of dates to sync"""
        dates = []
        today = datetime.now().date()
        for i in range(days):
            date = today - timedelta(days=i)
            dates.append(date)
        return dates

    def download_zone_file(self, ftp, zone, date_string, local_path):
        """Download zone CSV file"""
        try:
            # Try dated filename first
            filename = f"Zone{zone}_{date_string}.csv"
            remote_path = f"{self.config['remote_dir']}/{filename}"

            try:
                ftp.cwd(self.config['remote_dir'])
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {filename}', f.write)
                logger.info(f"  ↓ Downloaded: {filename}")
                return True
            except:
                # Try undated filename
                filename = f"Zone{zone}.csv"
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {filename}', f.write)
                logger.info(f"  ↓ Downloaded: {filename}")
                return True

        except Exception as e:
            logger.error(f"  ✗ Download failed for Zone{zone}: {e}")
            return False

    def parse_zone_csv(self, filepath):
        """Parse zone CSV file"""
        try:
            data = []
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            return data
        except Exception as e:
            logger.error(f"  ✗ Parse failed: {e}")
            return []

    def create_geojson(self, zone_data_list, date):
        """Create GeoJSON from zone data"""
        # This is a simplified version - you'll need to merge with control points
        # For now, creating a basic structure
        features = []

        for zone_idx, zone_data in enumerate(zone_data_list, 1):
            for row in zone_data:
                gridcode = row.get('GRIDCODE')
                if not gridcode:
                    continue

                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [0, 0]  # Placeholder - need control point lookup
                    },
                    'properties': {
                        'gridcode': gridcode,
                        'zone': zone_idx,
                        'forecasts': row,
                        'has_data': True
                    }
                }
                features.append(feature)

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        return geojson

    def sync(self):
        """Main sync function"""
        logger.info("=" * 70)
        logger.info("Ensemble FTP Sync Started")
        logger.info("=" * 70)

        stats = {'total': 0, 'downloaded': 0, 'ingested': 0, 'failed': 0}

        try:
            # Connect to FTP
            ftp = self.connect_ftp()

            # Get dates to sync
            dates = self.get_dates_to_sync()
            logger.info(f"Processing {len(dates)} dates")

            for date in dates:
                stats['total'] += 1
                date_string = date.strftime('%Y%m%d')

                logger.info(f"\nProcessing date: {date_string}")

                # Download all zones
                zone_data_list = []
                all_zones_downloaded = True

                for zone in self.config['zones']:
                    local_path = self.cache_dir / f"Zone{zone}_{date_string}.csv"

                    if not local_path.exists():
                        if not self.download_zone_file(ftp, zone, date_string, local_path):
                            all_zones_downloaded = False
                            break
                        stats['downloaded'] += 1

                    # Parse zone data
                    zone_data = self.parse_zone_csv(local_path)
                    zone_data_list.append(zone_data)

                if not all_zones_downloaded:
                    logger.warning(f"  ⚠ Skipping {date_string} - incomplete zone data")
                    stats['failed'] += 1
                    continue

                # Create GeoJSON
                geojson = self.create_geojson(zone_data_list, date)
                feature_count = len(geojson['features'])
                matched_count = sum(1 for f in geojson['features'] if f['properties'].get('has_data'))

                # Ingest into database
                if ingest_ensemble_geojson(date, date_string, geojson, feature_count, matched_count):
                    stats['ingested'] += 1
                else:
                    stats['failed'] += 1

            # Close FTP
            ftp.quit()

            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("Ensemble Sync Complete")
            logger.info(f"Total: {stats['total']} | Downloaded: {stats['downloaded']} | "
                       f"Ingested: {stats['ingested']} | Failed: {stats['failed']}")
            logger.info("=" * 70)

            return stats['failed'] == 0

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False


def run_ensemble_sync():
    """Entry point for Ensemble sync"""
    syncer = EnsembleSyncer()
    return syncer.sync()


if __name__ == "__main__":
    run_ensemble_sync()
