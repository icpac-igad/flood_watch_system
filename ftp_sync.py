#!/usr/bin/env python3
"""
Complete FTP Sync Script - Downloads and verifies all files from FTP server
Handles missing files, provides progress updates, and ensures complete sync

Author: Hillary Koros
Date: 2025-11-19
"""

import os
import sys
from ftplib import FTP
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load FTP credentials from .env file
load_dotenv()

# FTP Configuration
FTP_HOST = os.getenv('FTP_HOST')
FTP_PORT = int(os.getenv('FTP_PORT', 21))
FTP_USER = os.getenv('FTP_USER')
FTP_PASSWORD = os.getenv('FTP_PASSWORD')
REMOTE_DIR = os.getenv('FTP_REMOTE_DIR', 'output/Combined')
LOCAL_DIR = os.getenv('FTP_LOCAL_DIR', './downloaded_data')


def connect_ftp():
    """Connect to FTP server and return FTP object"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to FTP server at {FTP_HOST}:{FTP_PORT}...")
    ftp = FTP()
    ftp.connect(FTP_HOST, FTP_PORT, timeout=30)
    ftp.login(FTP_USER, FTP_PASSWORD)
    ftp.set_pasv(True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Connected successfully!")
    return ftp


def get_remote_files(ftp, remote_dir):
    """Get list of all files in remote directory"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching remote file list from '{remote_dir}'...")
    ftp.cwd(remote_dir)
    files = []
    ftp.retrlines('NLST', files.append)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(files)} files on server")
    return files


def get_local_files(local_dir):
    """Get list of all files in local directory"""
    if not os.path.exists(local_dir):
        return []
    return os.listdir(local_dir)


def download_file(ftp, remote_file, local_path, retry=True):
    """Download a single file from FTP server with retry logic"""
    try:
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f'RETR {remote_file}', f.write)
        return True
    except Exception as e:
        if retry:
            # Try once more
            try:
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {remote_file}', f.write)
                return True
            except:
                pass
        print(f"    ✗ Error downloading {remote_file}: {e}")
        return False


def download_files(ftp, files, local_dir, show_progress=True):
    """Download multiple files with progress tracking"""
    Path(local_dir).mkdir(parents=True, exist_ok=True)

    total = len(files)
    success = 0
    failed = 0
    failed_files = []

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting download of {total} files...")
    print("=" * 60)

    for idx, filename in enumerate(files, 1):
        local_path = os.path.join(local_dir, filename)

        if show_progress and idx % 50 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {idx}/{total} ({idx*100//total}%)")

        if download_file(ftp, filename, local_path):
            success += 1
        else:
            failed += 1
            failed_files.append(filename)

    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Download completed!")
    print(f"  ✓ Success: {success}")
    print(f"  ✗ Failed: {failed}")

    return failed_files


def verify_sync(remote_files, local_dir):
    """Verify that all remote files are downloaded locally"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Verifying download completeness...")

    remote_set = set(remote_files)
    local_files = get_local_files(local_dir)
    local_set = set(local_files)

    missing = remote_set - local_set

    print(f"  Remote files: {len(remote_set)}")
    print(f"  Local files:  {len(local_set)}")
    print(f"  Missing:      {len(missing)}")

    return list(missing)


def main():
    """Main sync function"""
    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("FTP SYNC - GeoSFM Data Download")
    print("=" * 60)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Remote: {FTP_HOST}:{REMOTE_DIR}")
    print(f"Local:  {LOCAL_DIR}")
    print("=" * 60 + "\n")

    try:
        # Step 1: Connect to FTP
        ftp = connect_ftp()

        # Step 2: Get remote file list
        remote_files = get_remote_files(ftp, REMOTE_DIR)

        # Step 3: Check what's already downloaded
        local_files = get_local_files(LOCAL_DIR)
        local_set = set(local_files)

        # Step 4: Determine files to download
        files_to_download = [f for f in remote_files if f not in local_set]

        if not files_to_download:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ All files already downloaded!")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(files_to_download)} new/missing files to download")

            # Step 5: Download files
            failed_files = download_files(ftp, files_to_download, LOCAL_DIR)

            # Step 6: Retry failed downloads
            if failed_files:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Retrying {len(failed_files)} failed files...")
                retry_failed = download_files(ftp, failed_files, LOCAL_DIR, show_progress=False)

                if retry_failed:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚠ Warning: {len(retry_failed)} files still failed after retry:")
                    for f in retry_failed:
                        print(f"    - {f}")

        # Step 7: Final verification
        missing = verify_sync(remote_files, LOCAL_DIR)

        # Step 8: Download any remaining missing files
        if missing:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Downloading {len(missing)} missing files...")
            download_files(ftp, missing, LOCAL_DIR, show_progress=False)

            # Final check
            missing = verify_sync(remote_files, LOCAL_DIR)

        # Close connection
        ftp.quit()

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("SYNC COMPLETE")
        print("=" * 60)
        print(f"End time:     {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:     {duration:.1f} seconds")
        print(f"Total files:  {len(remote_files)}")
        print(f"Local files:  {len(get_local_files(LOCAL_DIR))}")

        if missing:
            print(f"Status:       ⚠ INCOMPLETE - {len(missing)} files missing")
            print("\nMissing files:")
            for f in missing:
                print(f"  - {f}")
            return 1
        else:
            print(f"Status:       ✓ SUCCESS - All files synced!")

            # Calculate total size
            total_size = sum(os.path.getsize(os.path.join(LOCAL_DIR, f))
                           for f in os.listdir(LOCAL_DIR))
            print(f"Total size:   {total_size / (1024*1024):.1f} MB")

        print("=" * 60 + "\n")
        return 0

    except KeyboardInterrupt:
        print("\n\n[{datetime.now().strftime('%H:%M:%S')}] ⚠ Download interrupted by user")
        return 130
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
