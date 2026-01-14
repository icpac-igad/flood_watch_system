"""Download orchestrator - runs sync jobs on schedule"""
import time
from datetime import datetime
from .settings import SYNC_INTERVAL
from .floodproofs_sync import run_floodproofs_sync
from .ensemble_sync import run_ensemble_sync
from .logger_config import setup_logger

logger = setup_logger(__name__, 'download.log')


def run_all_syncs():
    """Run all data sync jobs"""
    logger.info("\n" + "=" * 80)
    logger.info(f"Starting FloodWatch data sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    success = True

    # Run FloodProofs sync
    logger.info("\n>>> Running FloodProofs SFTP sync...")
    if not run_floodproofs_sync():
        logger.error("✗ FloodProofs sync failed")
        success = False
    else:
        logger.info("✓ FloodProofs sync completed")

    # Run Ensemble sync
    logger.info("\n>>> Running Ensemble FTP sync...")
    if not run_ensemble_sync():
        logger.error("✗ Ensemble sync failed")
        success = False
    else:
        logger.info("✓ Ensemble sync completed")

    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✓ All syncs completed successfully")
    else:
        logger.warning("⚠ Some syncs failed - check logs")
    logger.info("=" * 80 + "\n")

    return success


def main():
    """Main loop - runs syncs on interval"""
    logger.info("FloodWatch Jobs - Download Service Started")
    logger.info(f"Sync interval: {SYNC_INTERVAL} seconds ({SYNC_INTERVAL/3600:.1f} hours)")

    while True:
        try:
            # Run syncs
            run_all_syncs()

            # Wait for next interval
            logger.info(f"Waiting {SYNC_INTERVAL} seconds until next sync...")
            time.sleep(SYNC_INTERVAL)

        except KeyboardInterrupt:
            logger.info("\nShutdown requested by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            logger.info("Waiting 60 seconds before retry...")
            time.sleep(60)


if __name__ == "__main__":
    main()
