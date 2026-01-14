"""Database utilities for FloodWatch jobs"""
import psycopg2
from psycopg2.extras import Json
from contextlib import contextmanager
from .settings import DB_CONFIG
from .logger_config import setup_logger

logger = setup_logger(__name__, 'database.log')


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def ingest_deterministic_geojson(data_date, date_string, geojson_data, feature_count):
    """
    Ingest merged deterministic GeoJSON into database

    Args:
        data_date: Date object (YYYY-MM-DD)
        date_string: Date string (YYYYMMDD)
        geojson_data: GeoJSON dict
        feature_count: Number of features

    Returns:
        bool: Success status
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if record exists
            cursor.execute(
                "SELECT id FROM floodproofs.merged_deterministic_geojson WHERE data_date = %s",
                (data_date,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing
                logger.info(f"Updating existing record for {data_date}")
                cursor.execute("""
                    UPDATE floodproofs.merged_deterministic_geojson
                    SET geojson_data = %s,
                        feature_count = %s,
                        file_count = 1,
                        processed_by = 'floodwatch_jobs',
                        updated_at = NOW()
                    WHERE data_date = %s
                """, (Json(geojson_data), feature_count, data_date))
            else:
                # Insert new
                logger.info(f"Creating new record for {data_date}")
                cursor.execute("""
                    INSERT INTO floodproofs.merged_deterministic_geojson
                    (data_date, date_string, geojson_data, feature_count, file_count,
                     file_path, processed_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 1, %s, 'floodwatch_jobs', NOW(), NOW())
                """, (data_date, date_string, Json(geojson_data), feature_count,
                      f"/data/floodproofs/{date_string}.geojson"))

            logger.info(f"✓ Ingested {feature_count} features for {data_date}")
            return True

    except Exception as e:
        logger.error(f"Failed to ingest deterministic data for {data_date}: {e}")
        return False


def ingest_ensemble_geojson(data_date, date_string, geojson_data, feature_count, matched_count):
    """
    Ingest ensemble forecast GeoJSON into database

    Args:
        data_date: Date object (YYYY-MM-DD)
        date_string: Date string (YYYYMMDD)
        geojson_data: GeoJSON dict
        feature_count: Total number of features
        matched_count: Number of features with forecast data

    Returns:
        bool: Success status
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if record exists
            cursor.execute(
                "SELECT id FROM floodproofs.ensemble_forecast_geojson WHERE data_date = %s",
                (data_date,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing
                logger.info(f"Updating existing ensemble record for {data_date}")
                cursor.execute("""
                    UPDATE floodproofs.ensemble_forecast_geojson
                    SET geojson_data = %s,
                        feature_count = %s,
                        matched_count = %s,
                        processed_by = 'floodwatch_jobs',
                        updated_at = NOW()
                    WHERE data_date = %s
                """, (Json(geojson_data), feature_count, matched_count, data_date))
            else:
                # Insert new
                logger.info(f"Creating new ensemble record for {data_date}")
                cursor.execute("""
                    INSERT INTO floodproofs.ensemble_forecast_geojson
                    (data_date, date_string, geojson_data, feature_count, matched_count,
                     processed_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'floodwatch_jobs', NOW(), NOW())
                """, (data_date, date_string, Json(geojson_data), feature_count, matched_count))

            logger.info(f"✓ Ingested {matched_count}/{feature_count} ensemble features for {data_date}")
            return True

    except Exception as e:
        logger.error(f"Failed to ingest ensemble data for {data_date}: {e}")
        return False
