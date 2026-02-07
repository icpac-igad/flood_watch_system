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


def run_wrf_rainfall_sync():
    """Run WRF Rainfall sync - weekly total and extreme rainfall"""
    logger.info(f"[{datetime.now()}] Running WRF Rainfall sync")

    try:
        from .wrf_rainfall_job import run_wrf_rainfall
        success = run_wrf_rainfall()

        if success:
            logger.info("WRF Rainfall sync completed successfully")
        else:
            logger.error("WRF Rainfall sync failed")

    except Exception as e:
        logger.exception(f"Error in WRF Rainfall sync: {e}")


def run_gcs_inundation_sync():
    """Run Google Flood Inundation History sync from GCS"""
    logger.info(f"[{datetime.now()}] Running GCS Inundation History sync")

    try:
        from .gcs_inundation_sync import sync_inundation_history
        stats = sync_inundation_history()

        if stats["failed"] == 0:
            logger.info(f"GCS inundation sync completed: {stats['ingested']} tiles ingested")
            # Refresh materialized view after successful ingest
            if stats["ingested"] > 0:
                from .database import get_db_connection
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT climate.refresh_inundation_geom()")
                    logger.info("Refreshed inundation geometry materialized view")
        else:
            logger.error(f"GCS inundation sync had {stats['failed']} failures")

    except Exception as e:
        logger.exception(f"Error in GCS inundation sync: {e}")


def run_db_backup():
    """Run daily database backup via pg_dump"""
    logger.info(f"[{datetime.now()}] Running database backup")

    try:
        import subprocess
        from .settings import DB_CONFIG

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = '/backups'
        dump_file = f'{backup_dir}/eafw_db_{timestamp}.dump'
        keep_days = 7

        result = subprocess.run([
            'pg_dump',
            '-h', DB_CONFIG['host'],
            '-p', str(DB_CONFIG['port']),
            '-U', DB_CONFIG['user'],
            '-d', DB_CONFIG['database'],
            '-Fc', '--no-owner', '--no-privileges',
            '-f', dump_file,
        ], capture_output=True, text=True, env={
            **__import__('os').environ,
            'PGPASSWORD': DB_CONFIG['password'],
        })

        if result.returncode == 0:
            import os
            size_mb = os.path.getsize(dump_file) / (1024 * 1024)
            logger.info(f"Database backup completed: {dump_file} ({size_mb:.0f} MB)")

            # Prune old backups
            import glob
            cutoff = datetime.now().timestamp() - (keep_days * 86400)
            for old_file in glob.glob(f'{backup_dir}/eafw_db_*.dump'):
                if os.path.getmtime(old_file) < cutoff:
                    os.remove(old_file)
                    logger.info(f"Pruned old backup: {old_file}")
        else:
            logger.error(f"pg_dump failed: {result.stderr}")

    except Exception as e:
        logger.exception(f"Database backup failed: {e}")


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

    # Schedule GCS Inundation History sync - weekly on Sunday at 02:00 UTC
    # Historical data (1999-2020) rarely changes, weekly check is sufficient
    scheduler.add_job(
        run_gcs_inundation_sync,
        CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='gcs_inundation_sync',
        name='Google Inundation History Sync',
        replace_existing=True
    )

    # Schedule WRF Rainfall sync - daily at 06:00 UTC
    # WRF weekly rainfall forecasts are updated daily
    scheduler.add_job(
        run_wrf_rainfall_sync,
        CronTrigger(hour=6, minute=0),
        id='wrf_rainfall_sync',
        name='WRF Rainfall Sync',
        replace_existing=True
    )

    # Schedule DB backup - daily at 5:30 PM (17:30) EAT
    # Runs after multimodal sync to capture fresh data
    scheduler.add_job(
        run_db_backup,
        CronTrigger(hour=17, minute=30),
        id='db_backup',
        name='Database Backup',
        replace_existing=True
    )

    # Run immediately on startup
    logger.info("Running initial sync on startup...")
    run_multimodal_sync()
    run_floodproofs_sync()
    run_gcs_inundation_sync()
    run_wrf_rainfall_sync()

    logger.info("Scheduler started. Jobs will run on schedule.")
    logger.info("Multimodal sync: Daily at 17:20 (5:20 PM)")
    logger.info("FloodProofs sync: 01:00, 07:00, 13:00, 19:00 UTC")
    logger.info("GCS Inundation sync: Weekly on Sunday at 02:00 UTC")
    logger.info("WRF Rainfall sync: Daily at 06:00 UTC")
    logger.info("Database backup: Daily at 17:30 (5:30 PM), keep 7 days")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    start_scheduler()
