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
    """Load river IDs and return period thresholds from the database.

    DB columns are rp2/rp10/rp25/rp50/rp100 (no "_yr" suffix)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT river_id, rp2, rp10, rp25, rp50, rp100
            FROM gha.geoglows_rivers
        """)
        rows = cursor.fetchall()

    rivers = {}
    for rid, rp2, rp10, rp25, rp50, rp100 in rows:
        rivers[rid] = {
            'rp2': rp2 or 0,
            'rp10': rp10 or 0,
            'rp25': rp25 or 0,
            'rp50': rp50 or 0,
            'rp100': rp100 or 0,
        }
    return rivers


def compute_alert_level(max_flow, thresholds):
    """Return the advisory bucket the max flow falls into.

    Aligned with the system-wide 4-tier palette:
      50 -> Extreme   (>= rp50 — also catches rp100 exceedance)
      25 -> Severe    (>= rp25)
      10 -> Moderate  (>= rp10)
       2 -> Less Risk (>= rp2)
       0 -> Normal    (below rp2)
    """
    if max_flow >= thresholds['rp50'] > 0:
        return 50
    elif max_flow >= thresholds['rp25'] > 0:
        return 25
    elif max_flow >= thresholds['rp10'] > 0:
        return 10
    elif max_flow >= thresholds['rp2'] > 0:
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

    # Process in BIG batches using zarr orthogonal indexing. The previous
    # per-river loop issued 300k+ separate S3 requests (≈ 4-8 h total). One
    # `oindex` call fetches a whole chunk at once, so the same work completes
    # in a handful of minutes. Sorting indices first keeps requested river
    # slices contiguous along the rivid chunk dimension, which lets zarr/s3fs
    # merge adjacent chunk reads.
    qout = z['Qout']
    total = len(matching_indices)

    order = np.argsort(matching_indices)
    sorted_indices = np.asarray(matching_indices, dtype=np.int64)[order]
    sorted_rids = np.asarray(matching_rids, dtype=np.int64)[order]

    CHUNK_RIVERS = 2000  # tune if zarr chunk shape differs; 2000 keeps memory
                         # modest (52*280*2000*4 B ≈ 113 MB per batch) while
                         # drastically reducing HTTP round-trips.
    max_flows = np.zeros(total, dtype=np.float32)

    for batch_start in range(0, total, CHUNK_RIVERS):
        batch_end = min(batch_start + CHUNK_RIVERS, total)
        batch_ids = sorted_indices[batch_start:batch_end].tolist()
        try:
            block = qout.oindex[:, :, batch_ids]  # shape (ens, time, N)
            median_ts = np.median(block, axis=0)   # shape (time, N)
            max_flows[batch_start:batch_end] = np.nanmax(median_ts, axis=0)
        except Exception as e:
            logger.error(f"Error reading batch {batch_start}-{batch_end}: {e}")
            continue
        logger.info(f"  Read {batch_end}/{total} rivers...")

    updates = []
    for rid, mf in zip(sorted_rids.tolist(), max_flows.tolist()):
        alert = compute_alert_level(mf, db_rivers[rid])
        updates.append((float(mf), alert, int(rid)))

    # Batch update DB
    logger.info(f"Updating {len(updates)} rivers in DB...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            from psycopg2.extras import execute_values
            execute_values(
                cursor,
                """UPDATE gha.geoglows_rivers AS t SET
                    max_forecast = v.flow,
                    alert_level  = v.rp,
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
