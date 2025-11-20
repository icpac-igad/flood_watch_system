import os
import sys
import argparse
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import paramiko
import rasterio
from rasterio.merge import merge as rio_merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
import numpy as np
import shutil
import subprocess


def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        raise SystemExit(f"Missing required environment variable: {name}")
    return val


class SFTPClient:
    def __init__(self, host: str, port: int, username: str, password: Optional[str] = None, key_path: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self._transport = None
        self._sftp = None

    def __enter__(self):
        self._transport = paramiko.Transport((self.host, self.port))
        if self.key_path:
            pkey = paramiko.RSAKey.from_private_key_file(self.key_path)
            self._transport.connect(username=self.username, pkey=pkey)
        else:
            self._transport.connect(username=self.username, password=self.password)
        self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        return self._sftp

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._sftp:
                self._sftp.close()
        finally:
            if self._transport:
                self._transport.close()


def sorted_dirs_numeric(entries: List[paramiko.SFTPAttributes]) -> List[paramiko.SFTPAttributes]:
    def key(e):
        try:
            return int(e.filename)
        except ValueError:
            return e.filename
    return sorted([e for e in entries if str(e.filename).isdigit()], key=key)


def download_alert_groups(sftp: paramiko.SFTPClient, hmc_dir: str, daily_out_dir: str, date_string: str) -> Optional[str]:
    """Download raw HMC alert TIFFs for a given date into daily_out_dir/raw/<date>"""
    try:
        entries = sftp.listdir_attr(hmc_dir)
    except FileNotFoundError:
        logger.warning("HMC directory not found for download-only mode: %s", hmc_dir)
        return None

    tif_files = [e.filename for e in entries if e.filename.lower().endswith('.tif')]
    if not tif_files:
        logger.warning("No TIFF files to download in %s", hmc_dir)
        return None

    dest_dir = Path(daily_out_dir) / 'raw' / date_string
    dest_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for filename in tif_files:
        remote_path = f"{hmc_dir}/{filename}"
        dest_path = dest_dir / filename
        try:
            sftp.get(remote_path, str(dest_path))
            downloaded += 1
        except Exception as exc:
            logger.warning("Failed to download %s: %s", remote_path, exc)

    logger.info("Downloaded %s alert TIFFs to %s", downloaded, dest_dir)
    return str(dest_dir)


def find_latest_run(sftp: paramiko.SFTPClient, root: str) -> Tuple[str, str]:
    """
    Find the latest run directory under the given root following structure:
    root/YYYY/MM/DD/HH/0000
    Returns tuple (yyyymmdd, run_dir_full_path_to_0000)
    """
    years = sorted_dirs_numeric(sftp.listdir_attr(root))
    if not years:
        raise FileNotFoundError(f"No year directories under {root}")
    year = years[-1].filename

    months = sorted_dirs_numeric(sftp.listdir_attr(f"{root}/{year}"))
    if not months:
        raise FileNotFoundError(f"No month directories under {root}/{year}")
    month = months[-1].filename

    days = sorted_dirs_numeric(sftp.listdir_attr(f"{root}/{year}/{month}"))
    if not days:
        raise FileNotFoundError(f"No day directories under {root}/{year}/{month}")
    day = days[-1].filename

    hours = sorted_dirs_numeric(sftp.listdir_attr(f"{root}/{year}/{month}/{day}"))
    if not hours:
        raise FileNotFoundError(f"No hour directories under {root}/{year}/{month}/{day}")
    hour = hours[-1].filename

    # Prefer subrun folder "0000" if present, else pick last numeric folder
    subruns = sorted_dirs_numeric(sftp.listdir_attr(f"{root}/{year}/{month}/{day}/{hour}"))
    subrun = None
    if subruns:
        subrun = [s.filename for s in subruns if s.filename == '0000']
        subrun = subrun[0] if subrun else subruns[-1].filename
    else:
        subrun = '0000'

    run_dir = f"{root}/{year}/{month}/{day}/{hour}/{subrun}"
    yyyymmdd = f"{year}{int(month):02d}{int(day):02d}"
    return yyyymmdd, run_dir


def merge_daily_alerts_from_hmc(sftp: paramiko.SFTPClient, hmc_dir: str, out_path: str) -> Optional[str]:
    """
    Download all .tif in HMC folder, merge them into a single GeoTIFF, write to out_path.
    Returns the output file path or None if no rasters found.
    """
    try:
        entries = sftp.listdir_attr(hmc_dir)
    except FileNotFoundError:
        logger.warning("HMC directory not found: %s", hmc_dir)
        return None

    # Prefer the HMC mosaics if present; else fallback to any tif
    tif_files = [e.filename for e in entries if e.filename.lower().endswith('_mosaic_alert_level.tif')]
    if not tif_files:
        tif_files = [e.filename for e in entries if e.filename.lower().endswith('.tif')]
    if not tif_files:
        logger.warning("No alert TIFFs found in %s", hmc_dir)
        return None

    tmpdir = tempfile.TemporaryDirectory()
    local_files = []
    for fname in tif_files:
        remote = f"{hmc_dir}/{fname}"
        local = os.path.join(tmpdir.name, fname)
        sftp.get(remote, local)
        local_files.append(local)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        os.chmod(os.path.dirname(out_path), 0o777)
    except Exception:
        pass

    gdalwarp = shutil.which('gdalwarp')
    gdalbuildvrt = shutil.which('gdalbuildvrt')
    gdal_translate = shutil.which('gdal_translate')

    if gdalwarp and gdalbuildvrt and gdal_translate:
        try:
            norm_files = []
            for i, src in enumerate(local_files):
                norm = os.path.join(tmpdir.name, f"norm_{i}.tif")
                cmd = [
                    gdalwarp, '-q', '-r', 'near', '-of', 'GTiff',
                    '-co', 'COMPRESS=LZW', src, norm
                ]
                subprocess.check_call(cmd)
                norm_files.append(norm)

            vrt_path = os.path.join(tmpdir.name, 'mosaic.vrt')
            cmd_vrt = [gdalbuildvrt, '-q', '-resolution', 'highest', vrt_path, *norm_files]
            subprocess.check_call(cmd_vrt)

            cmd_translate = [gdal_translate, '-co', 'COMPRESS=LZW', vrt_path, out_path]
            subprocess.check_call(cmd_translate)
            logger.info('Merged %s rasters into %s using GDAL pipeline', len(local_files), out_path)
            return out_path
        finally:
            tmpdir.cleanup()

    # Fall back to rasterio merge with max blending
    logger.warning('GDAL utilities not available; falling back to rasterio-based max merge for %s', out_path)
    try:
        datasets = [rasterio.open(src) for src in local_files]
        try:
            merged, out_transform = rio_merge(datasets, method='max')
            out_meta = datasets[0].meta.copy()
            out_meta.update({
                'height': merged.shape[1],
                'width': merged.shape[2],
                'transform': out_transform,
                'compress': 'lzw'
            })

            with rasterio.open(out_path, 'w', **out_meta) as dest:
                dest.write(merged)
                dest.nodata = 0

            logger.info('Merged %s rasters into %s using rasterio fallback', len(local_files), out_path)
            return out_path
        finally:
            for ds in datasets:
                ds.close()
            tmpdir.cleanup()
    except Exception as exc:
        logger.exception('Rasterio fallback merge failed for %s: %s', out_path, exc)
        return None


def copy_latest_inundation_tif(sftp: paramiko.SFTPClient, run_dir: str, out_dir: str) -> Optional[str]:
    """
    Copy the flood hazard GeoTIFF from latest run directory to out_dir.
    Returns the destination path or None if not found.
    """
    entries = sftp.listdir_attr(run_dir)
    candidates = [e.filename for e in entries if e.filename.lower().endswith('.tif')]
    # Prefer the specific naming pattern
    preferred = [f for f in candidates if f.startswith('flood_hazard_map_floodproofs_')]
    chosen = preferred[0] if preferred else (candidates[0] if candidates else None)
    if not chosen:
        logger.warning("No inundation GeoTIFFs found in %s", run_dir)
        return None
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, chosen)
    sftp.get(f"{run_dir}/{chosen}", dest)
    print(f"Copied inundation GeoTIFF to {dest}")
    return dest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sync daily alerts (merge) and inundation (copy) from SFTP into named volumes.")
    parser.add_argument('--alerts-root', default=os.getenv('SFTP_ALERTS_ROOT', '/home/floodproofs/fp-eastafrica/storage/impact_assessment/fp_impact_forecast/nwp_gfs-det'))
    parser.add_argument('--inundation-root', default=os.getenv('SFTP_INUNDATION_ROOT', '/home/floodproofs/fp-eastafrica/storage/impact_assessment/fp_impact_forecast/nwp_gfs-det'))
    parser.add_argument('--date', help='Date to process in YYYYMMDD. If omitted and no range is given, finds latest run.')
    parser.add_argument('--dates', help='Comma-separated list of dates YYYYMMDD to process, e.g. 20250909,20250910')
    parser.add_argument('--start-date', dest='start_date', help='Start date YYYYMMDD (inclusive) for range processing')
    parser.add_argument('--end-date', dest='end_date', help='End date YYYYMMDD (inclusive) for range processing')
    parser.add_argument('--only', choices=['alerts', 'inundation', 'both'], default='both')
    parser.add_argument('--download-only', action='store_true', help='Skip merging; download raw alert TIFFs into local storage')

    args = parser.parse_args(argv)

    host = env('SFTP_HOST', required=True)
    port = int(env('SFTP_PORT', '22'))
    user = env('SFTP_USER', required=True)
    password = env('SFTP_PASSWORD')
    key_path = env('SFTP_KEY_PATH')

    # Local target directories (shared named volumes in containers; fall back to repo data folders for local runs)
    project_root = Path(__file__).resolve().parents[2]
    default_daily_dir = project_root / 'data' / 'merged_alerts' / 'daily'
    default_inundation_dir = project_root / 'data' / 'inundation_maps'

    daily_out_dir = env('DAILY_OUT_DIR', str(default_daily_dir))
    inundation_out_dir = env('INUNDATION_OUT_DIR', str(default_inundation_dir))

    # Ensure local output directories exist and are writable
    os.makedirs(daily_out_dir, exist_ok=True)
    os.makedirs(inundation_out_dir, exist_ok=True)
    try:
        os.chmod(daily_out_dir, 0o777)
        os.chmod(inundation_out_dir, 0o777)
    except Exception:
        pass

    def iter_dates() -> List[str]:
        dates: List[str] = []
        if args.dates:
            dates.extend([d.strip() for d in args.dates.split(',') if d.strip()])
        if args.start_date and args.end_date:
            from datetime import timedelta
            start = datetime.strptime(args.start_date, '%Y%m%d')
            end = datetime.strptime(args.end_date, '%Y%m%d')
            cur = start
            while cur <= end:
                dates.append(cur.strftime('%Y%m%d'))
                cur = cur + timedelta(days=1)
        if args.date:
            dates.append(args.date)
        return dates

    with SFTPClient(host, port, user, password=password, key_path=key_path) as sftp:
        rc = 0
        dates_to_process = iter_dates()

        if not dates_to_process:
            # Process only latest
            yyyymmdd, run_dir = find_latest_run(sftp, args.inundation_root)
            logger.info("Selected run date %s at %s", yyyymmdd, run_dir)

            if args.only in ('alerts', 'both'):
                hmc_dir = f"{run_dir}/HMC"
                out_file = os.path.join(daily_out_dir, f"hmc_alert_daily_{yyyymmdd}.tif")
                try:
                    if args.download_only:
                        download_alert_groups(sftp, hmc_dir, daily_out_dir, yyyymmdd)
                    else:
                        merged = merge_daily_alerts_from_hmc(sftp, hmc_dir, out_file)
                        if not merged:
                            rc = 1
                        else:
                            logger.info("Merged alert raster written to %s", merged)
                except Exception as e:
                    logger.exception("Failed to process daily alerts for %s: %s", yyyymmdd, e)
                    rc = 1

                if not args.download_only and os.path.exists(out_file):
                    try:
                        os.chmod(daily_out_dir, 0o777)
                        dates_file = os.path.join(daily_out_dir, 'available_dates.txt')
                        dates = set()
                        for name in os.listdir(daily_out_dir):
                            if name.startswith('hmc_alert_daily_') and name.endswith('.tif'):
                                dates.add(name.replace('hmc_alert_daily_', '').replace('.tif', ''))
                        with open(dates_file, 'w') as f:
                            for d in sorted(dates):
                                f.write(d + '\n')
                        os.chmod(dates_file, 0o666)
                        logger.info("Updated available_dates.txt with %s entries", len(dates))
                    except Exception as e:
                        logger.warning("Failed to update available_dates.txt: %s", e)

            if args.only in ('inundation', 'both'):
                try:
                    copied = copy_latest_inundation_tif(sftp, run_dir, inundation_out_dir)
                    if not copied:
                        rc = 1
                    else:
                        logger.info("Copied inundation raster to %s", copied)
                except Exception as e:
                    logger.exception("Failed to copy inundation raster for %s: %s", yyyymmdd, e)
                    rc = 1
        else:
            for d in dates_to_process:
                yyyy, mm, dd = d[:4], d[4:6], d[6:8]
                day_root = f"{args.inundation_root}/{yyyy}/{int(mm):02d}/{int(dd):02d}"
                try:
                    hours = sorted_dirs_numeric(sftp.listdir_attr(day_root))
                    if not hours:
                        print(f"No hour directories under {day_root}")
                        rc = 1
                        continue
                    hour = hours[-1].filename
                    subruns = sorted_dirs_numeric(sftp.listdir_attr(f"{day_root}/{hour}"))
                    subrun = [s.filename for s in subruns if s.filename == '0000']
                    subrun = subrun[0] if subrun else (subruns[-1].filename if subruns else '0000')
                    run_dir = f"{day_root}/{hour}/{subrun}"
                    logger.info("Selected run date %s at %s", d, run_dir)
                except FileNotFoundError:
                    logger.warning("Date root not found: %s", day_root)
                    rc = 1
                    continue

                if args.only in ('alerts', 'both'):
                    hmc_dir = f"{run_dir}/HMC"
                    out_file = os.path.join(daily_out_dir, f"hmc_alert_daily_{d}.tif")
                    try:
                        if args.download_only:
                            download_alert_groups(sftp, hmc_dir, daily_out_dir, d)
                        else:
                            merged = merge_daily_alerts_from_hmc(sftp, hmc_dir, out_file)
                            if not merged:
                                rc = 1
                            else:
                                logger.info("Merged alert raster written to %s", out_file)
                    except Exception as e:
                        logger.exception("Failed to process daily alerts for %s: %s", d, e)
                        rc = 1

                if args.only in ('inundation', 'both'):
                    try:
                        copied = copy_latest_inundation_tif(sftp, run_dir, inundation_out_dir)
                        if not copied:
                            rc = 1
                        else:
                            logger.info("Copied inundation raster to %s", copied)
                    except Exception as e:
                        logger.exception("Failed to copy inundation raster for %s: %s", d, e)
                        rc = 1

            # After range/list processing, update available_dates.txt once
            if not args.download_only:
                try:
                    os.chmod(daily_out_dir, 0o777)
                    dates_file = os.path.join(daily_out_dir, 'available_dates.txt')
                    dates = set()
                    for name in os.listdir(daily_out_dir):
                        if name.startswith('hmc_alert_daily_') and name.endswith('.tif'):
                            dates.add(name.replace('hmc_alert_daily_', '').replace('.tif', ''))
                    with open(dates_file, 'w') as f:
                        for d in sorted(dates):
                            f.write(d + '\n')
                    os.chmod(dates_file, 0o666)
                    logger.info("Updated available_dates.txt with %s entries", len(dates))
                except Exception as e:
                    logger.warning("Failed to update available_dates.txt: %s", e)

    return rc


project_root = Path(__file__).resolve().parents[2]
preferred_logs_dir = project_root / 'logs'
fallback_logs_dir = project_root / 'backend' / 'logs'

log_filename = f"sftp_sync_{datetime.now().strftime('%Y%m%d')}.log"
logger = logging.getLogger('sftp_sync')
logger.setLevel(logging.INFO)

log_path: Optional[Path] = None
for candidate in (preferred_logs_dir, fallback_logs_dir):
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(candidate / log_filename, mode='a', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.propagate = False
        log_path = candidate / log_filename
        break
    except PermissionError:
        continue

if log_path:
    logger.info('Initialized sftp_sync logging -> %s', log_path)
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('sftp_sync')
    logger.warning('Falling back to basicConfig logging; could not create log file')

logger.info('SFTP sync script imported')


if __name__ == '__main__':
    sys.exit(main())
