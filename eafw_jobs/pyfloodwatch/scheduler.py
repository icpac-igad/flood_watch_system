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
    """Run WRF Rainfall sync - weekly total and extreme rainfall + COG export"""
    logger.info(f"[{datetime.now()}] Running WRF Rainfall sync (includes COG export)")

    try:
        from .wrf_rainfall_job import run_wrf_rainfall
        success = run_wrf_rainfall()

        if success:
            logger.info("WRF Rainfall sync completed successfully (ingestion + COG export)")
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


def run_google_flood_sync_job():
    """Run Google Flood Forecasting API sync."""
    logger.info(f"[{datetime.now()}] Running Google Flood Forecast sync")

    try:
        from .google_flood_sync import run_google_flood_sync
        success = run_google_flood_sync()
        if success:
            logger.info("Google Flood sync completed successfully")
        else:
            logger.warning("Google Flood sync skipped or failed")
    except Exception as e:
        logger.exception(f"Error in Google Flood sync: {e}")


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


def run_email_report():
    """Send daily email report with job status summary"""
    logger.info(f"[{datetime.now()}] Sending daily email report")

    try:
        from .email_report import send_daily_report
        send_daily_report()
        logger.info("Daily email report sent")
    except Exception as e:
        logger.exception(f"Error sending email report: {e}")


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

    # Schedule multimodal sync - daily at 6:00 PM (18:00) East Africa Time
    # MikeHYDRO server uploads CSVs to Drive at 5:40 PM via rclone;
    # run at 6:00 PM to allow upload of ~3000 files to complete first.
    scheduler.add_job(
        run_multimodal_sync,
        CronTrigger(hour=18, minute=0),
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

    # Schedule Google Flood Forecast API sync - every 6 hours
    scheduler.add_job(
        run_google_flood_sync_job,
        CronTrigger(hour='0,6,12,18', minute=20),
        id='google_flood_sync',
        name='Google Flood Forecast Sync',
        replace_existing=True
    )

    # Schedule DB backup - daily at 6:30 PM (18:30) EAT
    # Runs after multimodal sync (18:00) to capture fresh data
    scheduler.add_job(
        run_db_backup,
        CronTrigger(hour=18, minute=30),
        id='db_backup',
        name='Database Backup',
        replace_existing=True
    )

    # Schedule daily email report - at 7:00 PM (19:00) EAT
    # Runs after backup to summarize the day's job results
    scheduler.add_job(
        run_email_report,
        CronTrigger(hour=19, minute=0),
        id='email_report',
        name='Daily Email Report',
        replace_existing=True
    )

    # Run immediately on startup
    logger.info("Running initial sync on startup...")
    run_multimodal_sync()
    run_floodproofs_sync()
    run_gcs_inundation_sync()
    run_wrf_rainfall_sync()
    run_google_flood_sync_job()

    logger.info("Scheduler started. Jobs will run on schedule.")
    logger.info("Multimodal sync: Daily at 18:00 (6:00 PM) EAT")
    logger.info("FloodProofs sync: 01:00, 07:00, 13:00, 19:00 EAT")
    logger.info("GCS Inundation sync: Weekly on Sunday at 02:00 EAT")
    logger.info("WRF Rainfall sync: Daily at 06:00 EAT")
    logger.info("Google Flood sync: 00:20, 06:20, 12:20, 18:20 EAT")
    logger.info("Database backup: Daily at 18:30 (6:30 PM) EAT, keep 7 days")
    logger.info("Email report: Daily at 19:00 (7:00 PM) EAT")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    start_scheduler()
