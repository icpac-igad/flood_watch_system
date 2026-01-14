"""FloodProofs SFTP sync module"""
import paramiko
import json
from datetime import datetime, timedelta
from pathlib import Path
from .settings import FLOODPROOFS_CONFIG, DATA_DIR, SYNC_DAYS
from .database import ingest_deterministic_geojson
from .logger_config import setup_logger

logger = setup_logger(__name__, 'floodproofs_sync.log')


class FloodProofsSyncer:
    """Syncs FloodProofs merged deterministic forecast data from SFTP"""

    def __init__(self):
        self.config = FLOODPROOFS_CONFIG
        self.cache_dir = DATA_DIR / 'floodproofs'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def connect_sftp(self):
        """Connect to SFTP server"""
        try:
            logger.info(f"Connecting to SFTP {self.config['host']}:{self.config['port']}")
            transport = paramiko.Transport((self.config['host'], self.config['port']))
            transport.connect(username=self.config['username'], password=self.config['password'])
            sftp = paramiko.SFTPClient.from_transport(transport)
            logger.info("✓ SFTP connected")
            return sftp, transport
        except Exception as e:
            logger.error(f"✗ SFTP connection failed: {e}")
            raise

    def get_dates_to_sync(self, days=SYNC_DAYS):
        """Generate list of dates to sync"""
        dates = []
        today = datetime.now().date()
        for i in range(days):
            date = today - timedelta(days=i)
            dates.append(date)
        return dates

    def download_file(self, sftp, filename, local_path):
        """Download file from SFTP"""
        try:
            remote_path = f"{self.config['remote_dir']}/{filename}"
            sftp.get(remote_path, str(local_path))
            logger.info(f"  ↓ Downloaded: {filename}")
            return True
        except Exception as e:
            logger.error(f"  ✗ Download failed for {filename}: {e}")
            return False

    def parse_and_ingest(self, filepath, data_date):
        """Parse GeoJSON and ingest into database"""
        try:
            with open(filepath, 'r') as f:
                geojson_data = json.load(f)

            if geojson_data.get('type') != 'FeatureCollection':
                logger.error(f"  ✗ Invalid GeoJSON format")
                return False

            features = geojson_data.get('features', [])
            feature_count = len(features)
            date_string = data_date.strftime('%Y%m%d')

            # Ingest into database
            return ingest_deterministic_geojson(
                data_date=data_date,
                date_string=date_string,
                geojson_data=geojson_data,
                feature_count=feature_count
            )

        except Exception as e:
            logger.error(f"  ✗ Parse/ingest failed: {e}")
            return False

    def sync(self):
        """Main sync function"""
        logger.info("=" * 70)
        logger.info("FloodProofs SFTP Sync Started")
        logger.info("=" * 70)

        stats = {'total': 0, 'downloaded': 0, 'ingested': 0, 'skipped': 0, 'failed': 0}

        try:
            # Connect to SFTP
            sftp, transport = self.connect_sftp()

            # Get dates to sync
            dates = self.get_dates_to_sync()
            logger.info(f"Processing {len(dates)} dates")

            for date in dates:
                stats['total'] += 1
                date_string = date.strftime('%Y%m%d')
                filename = f"merged_data_{date_string}.geojson"
                local_path = self.cache_dir / filename

                logger.info(f"\nProcessing: {filename}")

                # Download if not cached
                if not local_path.exists():
                    if not self.download_file(sftp, filename, local_path):
                        stats['failed'] += 1
                        continue
                    stats['downloaded'] += 1
                else:
                    logger.info(f"  ⊙ Using cached file")

                # Parse and ingest
                if self.parse_and_ingest(local_path, date):
                    stats['ingested'] += 1
                else:
                    stats['failed'] += 1

            # Close SFTP
            sftp.close()
            transport.close()

            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("FloodProofs Sync Complete")
            logger.info(f"Total: {stats['total']} | Downloaded: {stats['downloaded']} | "
                       f"Ingested: {stats['ingested']} | Failed: {stats['failed']}")
            logger.info("=" * 70)

            return stats['failed'] == 0

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False


def run_floodproofs_sync():
    """Entry point for FloodProofs sync"""
    syncer = FloodProofsSyncer()
    return syncer.sync()


if __name__ == "__main__":
    run_floodproofs_sync()
