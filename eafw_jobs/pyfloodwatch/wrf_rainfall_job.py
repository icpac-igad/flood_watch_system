"""Job: Download WRF rainfall forecasts from FTP and ingest directly to database"""
import subprocess
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

import numpy as np
import xarray as xr
import pandas as pd

from .settings import WRF_CONFIG, DATA_DIR
from .database import get_db_connection
from .logger_config import setup_logger

logger = setup_logger(__name__, 'wrf_rainfall.log')


class WRFRainfallJob:
    """Download WRF rainfall forecasts and ingest directly to database"""

    def __init__(self):
        self.config = WRF_CONFIG
        self.cache_dir = DATA_DIR / 'wrf'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_lftp_script(self, commands):
        """Build lftp script with SSL settings for weak DH keys"""
        script = f"""
set ftp:ssl-force true
set ssl:verify-certificate no
set ftp:ssl-protect-data true
set ssl:priority "NORMAL:-VERS-TLS1.3:+VERS-TLS1.2:+VERS-TLS1.1:+VERS-TLS1.0:-DH"
open -u {self.config['username']},{self.config['password']} ftp://{self.config['host']}
cd {self.config['remote_dir']}
{commands}
quit
"""
        return script

    def list_ftp_folders(self):
        """List folders on FTP using lftp"""
        try:
            script = self._get_lftp_script("cls -1")
            cmd = ['lftp', '-c', script]

            logger.info(f"Listing FTP folders from: {self.config['host']}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

            if result.returncode != 0:
                logger.error(f"Failed to list FTP: {result.stderr}")
                return []

            # Parse folder listing - each line is a folder name
            date_folders = []
            for line in result.stdout.strip().split('\n'):
                folder = line.strip().rstrip('/')
                if folder and len(folder) == 8 and folder.isdigit():
                    try:
                        datetime.strptime(folder, '%Y%m%d')
                        date_folders.append(folder)
                    except:
                        pass

            date_folders.sort(reverse=True)
            logger.info(f"Found {len(date_folders)} date folders, latest: {date_folders[0] if date_folders else 'none'}")
            return date_folders

        except Exception as e:
            logger.error(f"Failed to list FTP folders: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_latest_folder(self):
        """Get the most recent date folder from FTP"""
        folders = self.list_ftp_folders()
        if folders:
            return folders[0]
        return None

    def download_file(self, folder, filename):
        """Download file from FTP using lftp"""
        try:
            local_path = self.cache_dir / filename
            remote_path = f"{folder}/{filename}"

            # Remove old file if exists
            if local_path.exists():
                local_path.unlink()

            script = self._get_lftp_script(f"get {remote_path} -o {local_path}")
            cmd = ['lftp', '-c', script]

            logger.info(f"Downloading: {remote_path}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0 and local_path.exists() and local_path.stat().st_size > 0:
                logger.info(f"Downloaded {filename}: {local_path.stat().st_size} bytes")
                return local_path
            else:
                logger.error(f"Failed to download {filename}: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Download error for {filename}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def setup_database(self):
        """Create database tables and grid if not exists"""
        logger.info("Setting up database tables...")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Create schema
                cur.execute("CREATE SCHEMA IF NOT EXISTS wrf")

                # Create fishnet function if not exists (in wrf schema)
                cur.execute("""
                    CREATE OR REPLACE FUNCTION wrf.ST_CreateFishnet(
                        nrow integer, ncol integer,
                        xsize numeric(19,9), ysize numeric(19,9),
                        x0 numeric(19,9) DEFAULT 0, y0 numeric(19,9) DEFAULT 0,
                        OUT yrow integer, OUT xcol integer, OUT cell geometry
                    ) RETURNS SETOF record AS $$
                    SELECT i + 1 AS row, j + 1 AS col,
                           ST_Translate(cell, j * $3 + $5, i * $4 + $6) AS geom
                    FROM generate_series(0, $1 - 1) AS i,
                         generate_series(0, $2 - 1) AS j,
                         (SELECT ST_PolygonFromText(
                             'POLYGON((0 0, 0 '||$4||', '||$3||' '||$4||', '||$3||' 0,0 0))', 4326
                         ) AS cell) AS foo;
                    $$ LANGUAGE sql IMMUTABLE STRICT;
                """)

                # Create WRF grid table (381 lat x 326 lon, ~0.1 degree resolution)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS wrf.grid_01dd (
                        id SERIAL PRIMARY KEY,
                        yrow INTEGER NOT NULL,
                        xcol INTEGER NOT NULL,
                        cell GEOMETRY(Polygon, 4326) NOT NULL
                    )
                """)

                # Check if grid already populated
                cur.execute("SELECT COUNT(*) FROM wrf.grid_01dd")
                count = cur.fetchone()[0]

                if count == 0:
                    logger.info("Creating WRF fishnet grid (381 x 326)...")
                    cur.execute("""
                        INSERT INTO wrf.grid_01dd (yrow, xcol, cell)
                        SELECT yrow, xcol, cell
                        FROM wrf.ST_CreateFishnet(381, 326, 0.1, 0.1, 21.0, -14.0)
                    """)
                    logger.info("Grid created with 124,206 cells")

                # Create spatial index
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_wrf_grid_cell
                    ON wrf.grid_01dd USING GIST(cell)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_wrf_grid_rowcol
                    ON wrf.grid_01dd(yrow, xcol)
                """)

                # Create daily rainfall table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS wrf.daily_rainfall (
                        id SERIAL PRIMARY KEY,
                        grid_id INTEGER NOT NULL REFERENCES wrf.grid_01dd(id),
                        forecast_date DATE NOT NULL,
                        valid_date DATE NOT NULL,
                        rainfall_mm NUMERIC(10,2) NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(grid_id, forecast_date, valid_date)
                    )
                """)

                cur.execute("CREATE INDEX IF NOT EXISTS idx_wrf_daily_forecast ON wrf.daily_rainfall(forecast_date)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wrf_daily_valid ON wrf.daily_rainfall(valid_date)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wrf_daily_grid ON wrf.daily_rainfall(grid_id)")

                # Create extreme rainfall table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS wrf.extreme_rainfall (
                        id SERIAL PRIMARY KEY,
                        grid_id INTEGER NOT NULL REFERENCES wrf.grid_01dd(id),
                        forecast_date DATE NOT NULL,
                        f90_mm NUMERIC(10,2),
                        f95_mm NUMERIC(10,2),
                        f99_mm NUMERIC(10,2),
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(grid_id, forecast_date)
                    )
                """)

                cur.execute("CREATE INDEX IF NOT EXISTS idx_wrf_extreme_forecast ON wrf.extreme_rainfall(forecast_date)")

                # Create MapServer query functions
                cur.execute("""
                    CREATE OR REPLACE FUNCTION wrf.get_daily_rainfall(p_valid_date DATE)
                    RETURNS TABLE(id INTEGER, rainfall_mm NUMERIC, cell GEOMETRY) AS $$
                    SELECT g.id, r.rainfall_mm, g.cell
                    FROM wrf.grid_01dd g
                    JOIN wrf.daily_rainfall r ON g.id = r.grid_id
                    WHERE r.valid_date = p_valid_date AND r.rainfall_mm > 0;
                    $$ LANGUAGE sql STABLE;
                """)

                cur.execute("""
                    CREATE OR REPLACE FUNCTION wrf.get_extreme_rainfall(p_forecast_date DATE, p_percentile TEXT DEFAULT 'f95')
                    RETURNS TABLE(id INTEGER, rainfall_mm NUMERIC, cell GEOMETRY) AS $$
                    BEGIN
                        IF p_percentile = 'f90' THEN
                            RETURN QUERY SELECT g.id, r.f90_mm, g.cell FROM wrf.grid_01dd g
                            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
                            WHERE r.forecast_date = p_forecast_date AND r.f90_mm > 0;
                        ELSIF p_percentile = 'f99' THEN
                            RETURN QUERY SELECT g.id, r.f99_mm, g.cell FROM wrf.grid_01dd g
                            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
                            WHERE r.forecast_date = p_forecast_date AND r.f99_mm > 0;
                        ELSE
                            RETURN QUERY SELECT g.id, r.f95_mm, g.cell FROM wrf.grid_01dd g
                            JOIN wrf.extreme_rainfall r ON g.id = r.grid_id
                            WHERE r.forecast_date = p_forecast_date AND r.f95_mm > 0;
                        END IF;
                    END;
                    $$ LANGUAGE plpgsql STABLE;
                """)

                conn.commit()
                logger.info("Database setup complete")

    def process_daily_rainfall(self, nc_data, folder_date):
        """Process PrecDaily.nc from memory/file and ingest to database"""
        logger.info("Processing daily rainfall...")

        try:
            # Handle both file path and BytesIO
            if isinstance(nc_data, (str, Path)):
                ds = xr.open_dataset(nc_data)
            else:
                # Write to temp file for xarray (required for netcdf)
                with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp:
                    tmp.write(nc_data.read())
                    tmp_path = tmp.name
                ds = xr.open_dataset(tmp_path)

            lats = ds['lat'].values
            lons = ds['lon'].values
            times = ds['time'].values
            rain = ds['dailyrain'].values

            # Convert times to dates
            dates = []
            for t in times:
                if hasattr(t, 'astype'):
                    # numpy datetime64
                    dates.append(pd.Timestamp(t).to_pydatetime().date())
                else:
                    dates.append(t)

            ds.close()

            forecast_date = datetime.strptime(folder_date, '%Y%m%d').date()
            logger.info(f"Forecast date: {forecast_date}, Valid dates: {dates}")

            # Build grid lookup
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get grid id lookup
                    cur.execute("SELECT id, yrow, xcol FROM wrf.grid_01dd")
                    grid_lookup = {(row[1], row[2]): row[0] for row in cur.fetchall()}
                    logger.info(f"Loaded {len(grid_lookup)} grid cells")

                    # Delete existing data for this forecast date
                    cur.execute("DELETE FROM wrf.daily_rainfall WHERE forecast_date = %s", (forecast_date,))

                    # Prepare batch insert
                    insert_count = 0
                    batch = []
                    batch_size = 10000

                    for t_idx, valid_date in enumerate(dates):
                        for lat_idx in range(len(lats)):
                            for lon_idx in range(len(lons)):
                                value = rain[t_idx, lat_idx, lon_idx]
                                if value != -9999 and not np.isnan(value) and value > 0:
                                    yrow = lat_idx + 1
                                    xcol = lon_idx + 1
                                    grid_id = grid_lookup.get((yrow, xcol))
                                    if grid_id:
                                        batch.append((grid_id, forecast_date, valid_date, float(value)))
                                        insert_count += 1

                                        if len(batch) >= batch_size:
                                            cur.executemany("""
                                                INSERT INTO wrf.daily_rainfall (grid_id, forecast_date, valid_date, rainfall_mm)
                                                VALUES (%s, %s, %s, %s)
                                                ON CONFLICT (grid_id, forecast_date, valid_date) DO UPDATE SET rainfall_mm = EXCLUDED.rainfall_mm
                                            """, batch)
                                            batch = []
                                            logger.info(f"  Inserted {insert_count} records...")

                    # Insert remaining
                    if batch:
                        cur.executemany("""
                            INSERT INTO wrf.daily_rainfall (grid_id, forecast_date, valid_date, rainfall_mm)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (grid_id, forecast_date, valid_date) DO UPDATE SET rainfall_mm = EXCLUDED.rainfall_mm
                        """, batch)

                    conn.commit()
                    logger.info(f"Saved {insert_count} daily rainfall records")

            return True
        except Exception as e:
            logger.error(f"Failed to process daily rainfall: {e}")
            import traceback
            traceback.print_exc()
            return False

    def process_extreme_rainfall(self, nc_data, folder_date):
        """Process PrecExtreme.nc from memory/file and ingest to database"""
        logger.info("Processing extreme rainfall...")

        try:
            if isinstance(nc_data, (str, Path)):
                ds = xr.open_dataset(nc_data)
            else:
                with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp:
                    tmp.write(nc_data.read())
                    tmp_path = tmp.name
                ds = xr.open_dataset(tmp_path)

            lats = ds['lat'].values
            lons = ds['lon'].values
            f90 = ds['f90'].values if 'f90' in ds else None
            f95 = ds['f95'].values if 'f95' in ds else None
            f99 = ds['f99'].values if 'f99' in ds else None

            ds.close()

            forecast_date = datetime.strptime(folder_date, '%Y%m%d').date()

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, yrow, xcol FROM wrf.grid_01dd")
                    grid_lookup = {(row[1], row[2]): row[0] for row in cur.fetchall()}

                    cur.execute("DELETE FROM wrf.extreme_rainfall WHERE forecast_date = %s", (forecast_date,))

                    insert_count = 0
                    batch = []
                    batch_size = 10000

                    for lat_idx in range(len(lats)):
                        for lon_idx in range(len(lons)):
                            yrow = lat_idx + 1
                            xcol = lon_idx + 1
                            grid_id = grid_lookup.get((yrow, xcol))

                            if not grid_id:
                                continue

                            f90_val = f95_val = f99_val = None

                            if f90 is not None:
                                val = f90[lat_idx, lon_idx]
                                if val != -9999 and not np.isnan(val) and val > 0:
                                    f90_val = float(val)

                            if f95 is not None:
                                val = f95[lat_idx, lon_idx]
                                if val != -9999 and not np.isnan(val) and val > 0:
                                    f95_val = float(val)

                            if f99 is not None:
                                val = f99[lat_idx, lon_idx]
                                if val != -9999 and not np.isnan(val) and val > 0:
                                    f99_val = float(val)

                            if f90_val or f95_val or f99_val:
                                batch.append((grid_id, forecast_date, f90_val, f95_val, f99_val))
                                insert_count += 1

                                if len(batch) >= batch_size:
                                    cur.executemany("""
                                        INSERT INTO wrf.extreme_rainfall (grid_id, forecast_date, f90_mm, f95_mm, f99_mm)
                                        VALUES (%s, %s, %s, %s, %s)
                                        ON CONFLICT (grid_id, forecast_date) DO UPDATE SET
                                            f90_mm = COALESCE(EXCLUDED.f90_mm, wrf.extreme_rainfall.f90_mm),
                                            f95_mm = COALESCE(EXCLUDED.f95_mm, wrf.extreme_rainfall.f95_mm),
                                            f99_mm = COALESCE(EXCLUDED.f99_mm, wrf.extreme_rainfall.f99_mm)
                                    """, batch)
                                    batch = []

                    if batch:
                        cur.executemany("""
                            INSERT INTO wrf.extreme_rainfall (grid_id, forecast_date, f90_mm, f95_mm, f99_mm)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (grid_id, forecast_date) DO UPDATE SET
                                f90_mm = COALESCE(EXCLUDED.f90_mm, wrf.extreme_rainfall.f90_mm),
                                f95_mm = COALESCE(EXCLUDED.f95_mm, wrf.extreme_rainfall.f95_mm),
                                f99_mm = COALESCE(EXCLUDED.f99_mm, wrf.extreme_rainfall.f99_mm)
                        """, batch)

                    conn.commit()
                    logger.info(f"Saved {insert_count} extreme rainfall records")

            return True
        except Exception as e:
            logger.error(f"Failed to process extreme rainfall: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run(self, folder_date=None):
        """Run the WRF rainfall job"""
        logger.info("=" * 70)
        logger.info("WRF Rainfall Job Started")
        logger.info("=" * 70)

        self.setup_database()

        # Get folder to process
        if folder_date:
            folder = folder_date
        else:
            folder = self.get_latest_folder()

        if not folder:
            logger.error("No folder to process")
            return False

        logger.info(f"Processing folder: {folder}")

        # Download and process PrecDaily.nc
        daily_path = self.download_file(folder, 'PrecDaily.nc')
        if daily_path:
            self.process_daily_rainfall(daily_path, folder)
            # Clean up downloaded file
            try:
                daily_path.unlink()
            except:
                pass

        # Download and process PrecExtreme.nc
        extreme_path = self.download_file(folder, 'PrecExtreme.nc')
        if extreme_path:
            self.process_extreme_rainfall(extreme_path, folder)
            # Clean up downloaded file
            try:
                extreme_path.unlink()
            except:
                pass

        logger.info("WRF Rainfall Job Completed")
        return True


def run_wrf_rainfall(folder_date=None):
    """Entry point"""
    job = WRFRainfallJob()
    return job.run(folder_date)


if __name__ == "__main__":
    run_wrf_rainfall()
