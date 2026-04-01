"""GEOGloWS v2 Forecast Sync - fetches river discharge forecasts from S3 Zarr
and updates alert levels for GHA rivers based on return period exceedance."""

import numpy as np
from datetime import datetime, timedelta
from .database import get_db_connection
from .logger_config import setup_logger

logger = setup_logger(__name__, 'geoglows_sync.log')


def get_forecast_date():
    """Get the latest available forecast date (today or yesterday)."""
    today = datetime.utcnow().strftime('%Y%m%d')
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d')

    try:
        import s3fs
        fs = s3fs.S3FileSystem(anon=True)
        if fs.exists(f's3://geoglows-v2-forecasts/{today}00.zarr/.zmetadata'):
            return f'{today}00'
        elif fs.exists(f's3://geoglows-v2-forecasts/{yesterday}00.zarr/.zmetadata'):
            return f'{yesterday}00'
    except Exception as e:
        logger.warning(f"Error checking forecast dates: {e}")

    return f'{today}00'


def load_db_rivers():
    """Load river IDs and return period thresholds from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT river_id, rp_2yr, rp_10yr, rp_25yr, rp_50yr
            FROM gha.geoglows_rivers
        """)
        rows = cursor.fetchall()

    rivers = {}
    for rid, rp2, rp10, rp25, rp50 in rows:
        rivers[rid] = {
            'rp_2yr': rp2 or 0,
            'rp_10yr': rp10 or 0,
            'rp_25yr': rp25 or 0,
            'rp_50yr': rp50 or 0,
        }
    return rivers


def compute_alert_level(max_flow, thresholds):
    """Determine alert level based on return period exceedance."""
    if max_flow >= thresholds['rp_50yr'] > 0:
        return 50
    elif max_flow >= thresholds['rp_25yr'] > 0:
        return 25
    elif max_flow >= thresholds['rp_10yr'] > 0:
        return 10
    elif max_flow >= thresholds['rp_2yr'] > 0:
        return 2
    return 0


def run_geoglows_sync():
    """Main sync function - reads forecast from S3 Zarr and updates DB."""
    try:
        import s3fs
        import zarr
    except ImportError:
        logger.error("s3fs/zarr not installed. pip install s3fs zarr")
        return False

    forecast_date = get_forecast_date()
    zarr_path = f's3://geoglows-v2-forecasts/{forecast_date}.zarr'
    logger.info(f"GEOGloWS sync starting - forecast: {forecast_date}")

    # Load river IDs and thresholds from DB
    db_rivers = load_db_rivers()
    if not db_rivers:
        logger.error("No rivers in gha.geoglows_rivers table")
        return False
    logger.info(f"Loaded {len(db_rivers)} rivers from DB")

    # Open Zarr store
    try:
        fs = s3fs.S3FileSystem(anon=True)
        store = s3fs.S3Map(root=zarr_path, s3=fs)
        z = zarr.open(store, mode='r')
    except Exception as e:
        logger.error(f"Failed to open Zarr: {e}")
        return False

    # Qout shape: (52 ensemble, 280 time, 6838900 rivid)
    forecast_rivids = z['rivid'][:]
    logger.info(f"Forecast has {len(forecast_rivids)} rivers globally")

    # Build index mapping for our rivers
    db_id_set = set(db_rivers.keys())
    matching_indices = []
    matching_rids = []
    for i, rid in enumerate(forecast_rivids):
        if int(rid) in db_id_set:
            matching_indices.append(i)
            matching_rids.append(int(rid))

    logger.info(f"Found {len(matching_indices)} matching rivers in forecast")

    if not matching_indices:
        logger.warning("No matching rivers found in forecast")
        return False

    # Process in batches - read chunks of rivers
    updates = []
    batch_size = 500
    total = len(matching_indices)

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_indices = matching_indices[batch_start:batch_end]
        batch_rids = matching_rids[batch_start:batch_end]

        try:
            for idx, rid in zip(batch_indices, batch_rids):
                # Read all ensembles for this river: shape (52, 280)
                data = z['Qout'][:, :, idx]
                # Median across ensembles, then max across time
                median_ts = np.median(data, axis=0)
                max_flow = float(np.nanmax(median_ts))

                alert = compute_alert_level(max_flow, db_rivers[rid])
                updates.append((max_flow, alert, rid))
        except Exception as e:
            logger.error(f"Error reading batch {batch_start}-{batch_end}: {e}")
            continue

        if (batch_start // batch_size) % 10 == 0:
            logger.info(f"  Processed {batch_end}/{total} rivers...")

    # Batch update DB
    logger.info(f"Updating {len(updates)} rivers in DB...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            from psycopg2.extras import execute_values
            execute_values(
                cursor,
                """UPDATE gha.geoglows_rivers AS t SET
                    forecast_flow = v.flow,
                    return_period = v.rp,
                    forecast_date = NOW(),
                    updated_at = NOW()
                FROM (VALUES %s) AS v(flow, rp, rid)
                WHERE t.river_id = v.rid""",
                updates,
                template="(%s::real, %s::smallint, %s::integer)"
            )
            conn.commit()
    except Exception as e:
        logger.error(f"DB update failed: {e}")
        return False

    # Log summary
    alerts = {}
    for _, alert, _ in updates:
        label = {0: 'Normal', 2: '2yr', 10: '10yr', 25: '25yr', 50: '50yr'}.get(alert, str(alert))
        alerts[label] = alerts.get(label, 0) + 1

    logger.info(f"GEOGloWS sync complete - {len(updates)} rivers updated")
    for label, count in sorted(alerts.items()):
        logger.info(f"  {label}: {count}")

    return True
