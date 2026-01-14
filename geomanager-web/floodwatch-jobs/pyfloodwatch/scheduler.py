"""Scheduler for FloodWatch jobs - runs like Celery Beat"""
import time
import signal
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .settings import SYNC_SOURCE, SYNC_INTERVAL
from .logger_config import setup_logger

logger = setup_logger(__name__, 'scheduler.log')


def run_multimodal_sync():
    """Run multimodal/ensemble sync based on configured source"""
    logger.info(f"[{datetime.now()}] Running multimodal sync (source: {SYNC_SOURCE})")

    try:
        if SYNC_SOURCE == 'drive':
            from .drive_sync import run_drive_sync
            success = run_drive_sync()
        elif SYNC_SOURCE == 'ftp':
            from .ensemble_sync import run_ensemble_sync
            success = run_ensemble_sync()
        else:
            logger.error(f"Unknown sync source: {SYNC_SOURCE}")
            return

        if success:
            logger.info("Multimodal sync completed successfully")
        else:
            logger.error("Multimodal sync failed")

    except Exception as e:
        logger.exception(f"Error in multimodal sync: {e}")


def run_floodproofs_sync():
    """Run FloodProofs deterministic sync"""
    logger.info(f"[{datetime.now()}] Running FloodProofs sync")

    try:
        from .floodproofs_sync import run_floodproofs_sync as sync_fp
        success = sync_fp()

        if success:
            logger.info("FloodProofs sync completed successfully")
        else:
            logger.error("FloodProofs sync failed")

    except Exception as e:
        logger.exception(f"Error in FloodProofs sync: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal, stopping scheduler...")
    sys.exit(0)


def start_scheduler():
    """Start the job scheduler"""
    logger.info("=" * 70)
    logger.info("FloodWatch Job Scheduler Starting")
    logger.info(f"Sync source: {SYNC_SOURCE}")
    logger.info(f"Sync interval: {SYNC_INTERVAL} seconds")
    logger.info("=" * 70)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    scheduler = BlockingScheduler()

    # Schedule multimodal sync - daily at 5:20 PM (17:20) East Africa Time
    # Data is available around 5:00 PM, run at 5:20 PM to allow for upload completion
    scheduler.add_job(
        run_multimodal_sync,
        CronTrigger(hour=17, minute=20),
        id='multimodal_sync',
        name='Multimodal Ensemble Sync',
        replace_existing=True
    )

    # Schedule FloodProofs sync - every 6 hours
    # Runs at 01:00, 07:00, 13:00, 19:00
    scheduler.add_job(
        run_floodproofs_sync,
        CronTrigger(hour='1,7,13,19', minute=0),
        id='floodproofs_sync',
        name='FloodProofs Deterministic Sync',
        replace_existing=True
    )

    # Run immediately on startup
    logger.info("Running initial sync on startup...")
    run_multimodal_sync()
    run_floodproofs_sync()

    logger.info("Scheduler started. Jobs will run on schedule.")
    logger.info("Multimodal sync: Daily at 17:20 (5:20 PM)")
    logger.info("FloodProofs sync: 01:00, 07:00, 13:00, 19:00 UTC")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    start_scheduler()
