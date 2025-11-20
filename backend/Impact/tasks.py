from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
def sync_floodproofs_daily():
    """
    Daily FloodProofs SFTP to Database sync task.
    Runs at 12:15 PM daily.
    Syncs only today's forecast data.

    For syncing multiple days or historical data, run manually:
    python manage.py sync_floodproofs_to_db --days N
    """
    logger.info("Starting daily FloodProofs sync task...")
    try:
        call_command('sync_floodproofs_to_db', '--days', '1')
        logger.info("✓ FloodProofs sync completed successfully")
    except Exception as e:
        logger.error(f"✗ FloodProofs sync failed: {str(e)}")
        raise


@shared_task
def sync_ensemble_daily():
    """
    Daily Ensemble Forecast FTP to Database sync task.
    Runs at 5:25 PM EAT (14:25 UTC) daily.

    FTP server updates data daily at 5:20 PM EAT, so this runs 5 minutes later.
    Downloads all Zone*.csv files from FTP, merges with control points,
    and saves to database with the date extracted from the forecast data.

    For manual sync, run:
    python manage.py sync_ensemble_from_ftp
    """
    logger.info("Starting daily Ensemble FTP sync task...")
    try:
        call_command('sync_ensemble_from_ftp')
        logger.info("✓ Ensemble FTP sync completed successfully")
    except Exception as e:
        logger.error(f"✗ Ensemble FTP sync failed: {str(e)}")
        raise