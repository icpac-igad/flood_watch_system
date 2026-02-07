"""Database utilities for FloodWatch jobs"""
import psycopg2
from psycopg2.extras import Json, execute_values
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
                "SELECT id FROM home_merged_deterministic_geojson WHERE data_date = %s",
                (data_date,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing
                logger.info(f"Updating existing record for {data_date}")
                cursor.execute("""
                    UPDATE home_merged_deterministic_geojson
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
                    INSERT INTO home_merged_deterministic_geojson
                    (data_date, date_string, geojson_data, feature_count, file_count,
                     file_path, processed_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 1, %s, 'floodwatch_jobs', NOW(), NOW())
                """, (data_date, date_string, Json(geojson_data), feature_count,
                      f"/data/floodproofs/{date_string}.geojson"))

            logger.info(f"Ingested {feature_count} features for {data_date}")
            return True

    except Exception as e:
        logger.error(f"Failed to ingest deterministic data for {data_date}: {e}")
        return False


def ingest_multimodal_forecasts(data_date, forecast_data, control_points):
    """
    Ingest multimodal forecasts into normalized gha.multimodal_forecasts table.

    Each CSV point has a list of forecasts (one per forecast_date). We batch-upsert
    all rows keyed by (point_id, data_date, forecast_date).

    Args:
        data_date: Date the forecast was issued (date object)
        forecast_data: dict of {(zone, gridcode): [forecast_dicts]}
                       Each forecast_dict has 'date' and model values.
        control_points: dict of {(zone, gridcode): [point_dicts]}
                        Each point_dict has 'point_id'.

    Returns:
        tuple: (success: bool, matched_count: int)
    """
    rows = []
    matched = 0

    for key, forecasts in forecast_data.items():
        points = control_points.get(key, [])
        if not points:
            continue

        matched += 1

        for point in points:
            point_id = point['point_id']
            for fc in forecasts:
                forecast_date = fc.get('date')
                if not forecast_date:
                    continue

                rows.append((
                    point_id,
                    data_date,
                    forecast_date,
                    fc.get('daily_avg'),
                    fc.get('daily_max'),
                    fc.get('daily_min'),
                    fc.get('GeoSFM'),
                    fc.get('Floodproof'),
                    fc.get('Mike_Hydro_RFE'),
                    fc.get('Mike_Hydro_CHIRP'),
                    fc.get('Mike_Hydro_IMERG'),
                ))

    if not rows:
        logger.warning(f"No forecast rows to ingest for {data_date}")
        return False, 0

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            execute_values(cursor, """
                INSERT INTO gha.multimodal_forecasts
                    (point_id, data_date, forecast_date,
                     daily_avg, daily_max, daily_min,
                     geosfm, floodproof,
                     mike_hydro_rfe, mike_hydro_chirp, mike_hydro_imerg)
                VALUES %s
                ON CONFLICT (point_id, data_date, forecast_date)
                DO UPDATE SET
                    daily_avg = EXCLUDED.daily_avg,
                    daily_max = EXCLUDED.daily_max,
                    daily_min = EXCLUDED.daily_min,
                    geosfm = EXCLUDED.geosfm,
                    floodproof = EXCLUDED.floodproof,
                    mike_hydro_rfe = EXCLUDED.mike_hydro_rfe,
                    mike_hydro_chirp = EXCLUDED.mike_hydro_chirp,
                    mike_hydro_imerg = EXCLUDED.mike_hydro_imerg
            """, rows, page_size=1000)

            logger.info(
                f"Ingested {len(rows)} forecast rows for {data_date} "
                f"({matched} points with data)"
            )
            return True, matched

    except Exception as e:
        logger.error(f"Failed to ingest multimodal forecasts for {data_date}: {e}")
        return False, 0


# Legacy JSONB ingest (kept for backwards compatibility, unused in new pipeline)
def ingest_multimodal_geojson(data_date, date_string, geojson_data, feature_count, matched_count):
    """Legacy: Ingest multimodal forecast as JSONB blob"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM home_multimodal_forecast_geojson WHERE data_date = %s",
                (data_date,)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE home_multimodal_forecast_geojson
                    SET geojson_data = %s, feature_count = %s, matched_count = %s,
                        processed_by = 'floodwatch_jobs', updated_at = NOW()
                    WHERE data_date = %s
                """, (Json(geojson_data), feature_count, matched_count, data_date))
            else:
                cursor.execute("""
                    INSERT INTO home_multimodal_forecast_geojson
                    (data_date, date_string, geojson_data, feature_count, matched_count,
                     processed_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'floodwatch_jobs', NOW(), NOW())
                """, (data_date, date_string, Json(geojson_data), feature_count, matched_count))

            logger.info(f"Ingested {matched_count}/{feature_count} multimodal features for {data_date}")
            return True
    except Exception as e:
        logger.error(f"Failed to ingest multimodal data for {data_date}: {e}")
        return False


ingest_ensemble_geojson = ingest_multimodal_geojson
