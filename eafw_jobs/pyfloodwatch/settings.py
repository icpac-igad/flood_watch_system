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
    'host': os.getenv('FLOODPROOFS_SFTP_HOST'),
    'port': int(os.getenv('FLOODPROOFS_SFTP_PORT', 22)),
    'username': os.getenv('FLOODPROOFS_SFTP_USER'),
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

# Google Flood Forecasting API sync configuration
GOOGLE_FLOOD_CONFIG = {
    'api_key': os.getenv('FLOODS_API_KEY'),
    'region_codes': [
        code.strip().upper()
        for code in os.getenv(
            'GOOGLE_FLOOD_REGION_CODES',
            'ET,KE,UG,SD,SS,RW,SO,DJ,ER,TZ,BI'
        ).split(',')
        if code.strip()
    ],
    'page_size': int(os.getenv('GOOGLE_FLOOD_PAGE_SIZE', 20000)),
    'status_chunk_size': int(os.getenv('GOOGLE_FLOOD_STATUS_CHUNK_SIZE', 500)),
    'model_chunk_size': int(os.getenv('GOOGLE_FLOOD_MODEL_CHUNK_SIZE', 200)),
    'forecast_chunk_size': int(os.getenv('GOOGLE_FLOOD_FORECAST_CHUNK_SIZE', 200)),
    'issued_lookback_days': int(os.getenv('GOOGLE_FLOOD_ISSUED_LOOKBACK_DAYS', 7)),
    'include_non_quality_verified': os.getenv('GOOGLE_FLOOD_INCLUDE_NON_QUALITY_VERIFIED', 'true').lower() == 'true',
    'include_gauges_without_hydro_model': os.getenv('GOOGLE_FLOOD_INCLUDE_GAUGES_WITHOUT_HYDRO_MODEL', 'true').lower() == 'true',
    'request_timeout_seconds': int(os.getenv('GOOGLE_FLOOD_REQUEST_TIMEOUT_SECONDS', 120)),
    'max_retries': int(os.getenv('GOOGLE_FLOOD_MAX_RETRIES', 4)),
    'base_backoff_seconds': float(os.getenv('GOOGLE_FLOOD_BASE_BACKOFF_SECONDS', 1.0)),
}

# Email notification settings
# Supports both SMTP_HOST and legacy SMTP_EMAIL_HOST env var names
EMAIL_CONFIG = {
    'enabled': os.getenv('EMAIL_NOTIFICATIONS_ENABLED', 'true').lower() == 'true',
    'smtp_host': os.getenv('SMTP_HOST', os.getenv('SMTP_EMAIL_HOST', 'smtp.gmail.com')),
    'smtp_port': int(os.getenv('SMTP_PORT', os.getenv('SMTP_EMAIL_PORT', 587))),
    'smtp_user': os.getenv('SMTP_USER', os.getenv('SMTP_EMAIL_HOST_USER', '')),
    'smtp_password': os.getenv('SMTP_PASSWORD', os.getenv('SMTP_EMAIL_HOST_PASSWORD', '')),
    'from_addr': os.getenv('EMAIL_FROM', os.getenv('SMTP_USER', os.getenv('SMTP_EMAIL_HOST_USER', ''))),
    'to_addrs': [
        addr.strip()
        for addr in os.getenv('EMAIL_TO', 'hkoros@icpac.net').split(',')
        if addr.strip()
    ],
}

# Create directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
