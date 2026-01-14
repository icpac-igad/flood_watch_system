"""
Celery tasks for scheduled data syncing.
"""
from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task(name='home.tasks.sync_floodproofs_daily')
def sync_floodproofs_daily():
    """
    Daily FloodProofs SFTP sync task.
    Syncs deterministic discharge forecast data.

    For manual sync:
        python manage.py sync_floodproofs_to_db --days 1
    """
    logger.info("Starting daily FloodProofs sync task...")
    try:
        call_command('sync_floodproofs_to_db', '--days', '1')
        logger.info("✓ FloodProofs sync completed successfully")
    except Exception as e:
        logger.error(f"✗ FloodProofs sync failed: {str(e)}")
        raise


@shared_task(name='home.tasks.sync_multimodal_daily')
def sync_multimodal_daily():
    """
    Daily Multimodal Forecast FTP sync task.
    Scheduled to run at 17:30 EAT (14:30 UTC) daily.

    FTP server updates data around 17:00 EAT, this runs 30 minutes later.
    Downloads Zone*.csv files from FTP, merges with control points,
    and saves to database.

    For manual sync:
        python manage.py sync_ensemble_from_ftp --days 1
    """
    logger.info("Starting daily Multimodal FTP sync task...")
    try:
        call_command('sync_ensemble_from_ftp', '--days', '1')
        logger.info("✓ Multimodal FTP sync completed successfully")
    except Exception as e:
        logger.error(f"✗ Multimodal FTP sync failed: {str(e)}")
        raise


@shared_task(name='home.tasks.sync_multimodal_backfill')
def sync_multimodal_backfill(days=30):
    """
    Backfill multimodal forecasts for multiple days.

    For manual backfill:
        python manage.py sync_ensemble_from_ftp --days 30
    """
    logger.info(f"Starting Multimodal backfill for {days} days...")
    try:
        call_command('sync_ensemble_from_ftp', '--days', str(days))
        logger.info(f"✓ Multimodal backfill completed for {days} days")
    except Exception as e:
        logger.error(f"✗ Multimodal backfill failed: {str(e)}")
        raise
