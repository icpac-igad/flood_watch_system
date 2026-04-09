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

            # Update the geomanager dataset's latest_date so the homepage widget
            # and API reflect the freshest available data_date (issue date).
            cursor.execute("""
                UPDATE geomanager_dataset
                SET latest_date = (
                    SELECT MAX(data_date)
                    FROM gha.multimodal_forecasts
                )
                WHERE title = 'Multi Model'
                  AND (latest_date IS NULL OR latest_date < %s)
            """, (data_date,))

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


def ensure_google_flood_table():
    """Create Google Flood API cache table if missing."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE SCHEMA IF NOT EXISTS gha")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gha.google_flood_points_latest (
                gauge_id TEXT PRIMARY KEY,
                point_id TEXT NOT NULL,
                admin_name TEXT,
                hybas_id BIGINT,
                country_code TEXT,
                region_code TEXT,
                source TEXT,
                site_name TEXT,
                river TEXT,
                data_date DATE,
                quality_verified BOOLEAN,
                model_quality_verified BOOLEAN,
                status_quality_verified BOOLEAN,
                latest_severity TEXT,
                latest_forecast_trend TEXT,
                latest_issued_time TIMESTAMPTZ,
                threshold_alert DOUBLE PRECISION,
                threshold_alarm DOUBLE PRECISION,
                threshold_emergency DOUBLE PRECISION,
                daily_avg DOUBLE PRECISION,
                daily_max DOUBLE PRECISION,
                daily_min DOUBLE PRECISION,
                forecasts_json JSONB,
                gauge_value_unit TEXT,
                gauge_model_id TEXT,
                confidence_level TEXT,
                confidence_score DOUBLE PRECISION,
                raw_status JSONB,
                raw_model JSONB,
                raw_forecast JSONB,
                geom geometry(Point, 4326),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS google_flood_points_latest_geom_gix
            ON gha.google_flood_points_latest USING GIST (geom)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS google_flood_points_latest_data_date_idx
            ON gha.google_flood_points_latest (data_date DESC)
        """)


def ingest_google_flood_points(records, prune_stale=True):
    """
    Upsert Google Flood API gauge rows into gha.google_flood_points_latest.

    Args:
        records: iterable of dict rows prepared by google_flood_sync module.
        prune_stale: if True, remove rows for gauges not present in current sync.

    Returns:
        tuple: (success: bool, upserted_count: int, pruned_count: int)
    """
    rows = list(records or [])
    if not rows:
        logger.warning("No Google Flood rows to ingest")
        return False, 0, 0

    ensure_google_flood_table()

    values = []
    gauge_ids = []
    for record in rows:
        gauge_id = record.get('gauge_id')
        if not gauge_id:
            continue

        gauge_ids.append(gauge_id)
        lon = record.get('longitude')
        lat = record.get('latitude')
        values.append((
            gauge_id,
            record.get('point_id') or gauge_id,
            record.get('admin_name'),
            record.get('hybas_id'),
            record.get('country_code'),
            record.get('region_code'),
            record.get('source'),
            record.get('site_name'),
            record.get('river'),
            record.get('data_date'),
            record.get('quality_verified'),
            record.get('model_quality_verified'),
            record.get('status_quality_verified'),
            record.get('latest_severity'),
            record.get('latest_forecast_trend'),
            record.get('latest_issued_time'),
            record.get('threshold_alert'),
            record.get('threshold_alarm'),
            record.get('threshold_emergency'),
            record.get('daily_avg'),
            record.get('daily_max'),
            record.get('daily_min'),
            Json(record.get('forecasts_json') or []),
            record.get('gauge_value_unit'),
            record.get('gauge_model_id'),
            record.get('confidence_level'),
            record.get('confidence_score'),
            Json(record.get('raw_status') or {}),
            Json(record.get('raw_model') or {}),
            Json(record.get('raw_forecast') or {}),
            lon,
            lat,
            lon,
            lat,
        ))

    if not values:
        logger.warning("No valid Google Flood rows to ingest after validation")
        return False, 0, 0

    unique_gauge_ids = list(dict.fromkeys(gauge_ids))

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            execute_values(cursor, """
                INSERT INTO gha.google_flood_points_latest (
                    gauge_id,
                    point_id,
                    admin_name,
                    hybas_id,
                    country_code,
                    region_code,
                    source,
                    site_name,
                    river,
                    data_date,
                    quality_verified,
                    model_quality_verified,
                    status_quality_verified,
                    latest_severity,
                    latest_forecast_trend,
                    latest_issued_time,
                    threshold_alert,
                    threshold_alarm,
                    threshold_emergency,
                    daily_avg,
                    daily_max,
                    daily_min,
                    forecasts_json,
                    gauge_value_unit,
                    gauge_model_id,
                    confidence_level,
                    confidence_score,
                    raw_status,
                    raw_model,
                    raw_forecast,
                    geom,
                    updated_at
                )
                VALUES %s
                ON CONFLICT (gauge_id)
                DO UPDATE SET
                    point_id = EXCLUDED.point_id,
                    admin_name = EXCLUDED.admin_name,
                    hybas_id = EXCLUDED.hybas_id,
                    country_code = EXCLUDED.country_code,
                    region_code = EXCLUDED.region_code,
                    source = EXCLUDED.source,
                    site_name = EXCLUDED.site_name,
                    river = EXCLUDED.river,
                    data_date = EXCLUDED.data_date,
                    quality_verified = EXCLUDED.quality_verified,
                    model_quality_verified = EXCLUDED.model_quality_verified,
                    status_quality_verified = EXCLUDED.status_quality_verified,
                    latest_severity = EXCLUDED.latest_severity,
                    latest_forecast_trend = EXCLUDED.latest_forecast_trend,
                    latest_issued_time = EXCLUDED.latest_issued_time,
                    threshold_alert = EXCLUDED.threshold_alert,
                    threshold_alarm = EXCLUDED.threshold_alarm,
                    threshold_emergency = EXCLUDED.threshold_emergency,
                    daily_avg = EXCLUDED.daily_avg,
                    daily_max = EXCLUDED.daily_max,
                    daily_min = EXCLUDED.daily_min,
                    forecasts_json = EXCLUDED.forecasts_json,
                    gauge_value_unit = EXCLUDED.gauge_value_unit,
                    gauge_model_id = EXCLUDED.gauge_model_id,
                    confidence_level = EXCLUDED.confidence_level,
                    confidence_score = EXCLUDED.confidence_score,
                    raw_status = EXCLUDED.raw_status,
                    raw_model = EXCLUDED.raw_model,
                    raw_forecast = EXCLUDED.raw_forecast,
                    geom = EXCLUDED.geom,
                    updated_at = NOW()
            """, values, template="""
                (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CASE
                        WHEN %s IS NULL OR %s IS NULL THEN NULL
                        ELSE ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    END,
                    NOW()
                )
            """, page_size=500)

            pruned_count = 0
            if prune_stale and unique_gauge_ids:
                cursor.execute(
                    """
                    DELETE FROM gha.google_flood_points_latest
                    WHERE gauge_id <> ALL(%s)
                    """,
                    (unique_gauge_ids,),
                )
                pruned_count = cursor.rowcount or 0

            logger.info(
                f"Ingested Google Flood rows: upserted={len(values)}, pruned={pruned_count}, unique_gauges={len(unique_gauge_ids)}"
            )
            return True, len(values), pruned_count
    except Exception as e:
        logger.error(f"Failed to ingest Google Flood points: {e}")
        return False, 0, 0
