"""Configuration settings for FloodWatch jobs"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))
LOGS_DIR = Path(os.getenv('LOGS_DIR', BASE_DIR / 'logs'))

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'eafw-pgdb'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'geomanager_web'),
    'user': os.getenv('DB_USER', 'geomanager'),
    'password': os.getenv('DB_PASSWORD'),
}

# FloodProofs SFTP configuration
FLOODPROOFS_CONFIG = {
    'host': os.getenv('FLOODPROOFS_SFTP_HOST', '197.254.113.173'),
    'port': int(os.getenv('FLOODPROOFS_SFTP_PORT', 22)),
    'username': os.getenv('FLOODPROOFS_SFTP_USER', 'floodproofs'),
    'password': os.getenv('FLOODPROOFS_SFTP_PASSWORD'),
    'remote_dir': os.getenv('FLOODPROOFS_REMOTE_DIR', '/home/floodproofs/merged_forecasts'),
    'file_pattern': 'merged_data_{date}.geojson',
}

# Ensemble FTP configuration
ENSEMBLE_CONFIG = {
    'host': os.getenv('ENSEMBLE_FTP_HOST'),
    'port': int(os.getenv('ENSEMBLE_FTP_PORT', 21)),
    'username': os.getenv('ENSEMBLE_FTP_USER'),
    'password': os.getenv('ENSEMBLE_FTP_PASSWORD'),
    'remote_dir': os.getenv('ENSEMBLE_REMOTE_DIR', '/output/Combined'),
    'zones': [1, 2, 3, 4, 5, 6],
    'file_pattern': 'Zone{zone}_{gridcode}.csv',
}

# Google Drive configuration
DRIVE_CONFIG = {
    'folder_id': os.getenv('DRIVE_FOLDER_ID'),
    'credentials_file': os.getenv('GOOGLE_CREDENTIALS_FILE', '/opt/credentials/google-credentials.json'),
}

# WRF Rainfall FTP configuration
WRF_CONFIG = {
    'host': os.getenv('WRF_FTP_HOST'),
    'port': int(os.getenv('WRF_FTP_PORT', 21)),
    'username': os.getenv('WRF_FTP_USER'),
    'password': os.getenv('WRF_FTP_PASSWORD'),
    'remote_dir': os.getenv('WRF_REMOTE_DIR', '/SharedData/wrf/weekly'),
    'files': ['PrecDaily.nc', 'PrecExtreme.nc'],
}

# Sync settings
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', 21600))  # 6 hours
SYNC_DAYS = int(os.getenv('SYNC_DAYS', 7))
SYNC_SOURCE = os.getenv('SYNC_SOURCE', 'drive')  # ftp, drive, local

# Create directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
