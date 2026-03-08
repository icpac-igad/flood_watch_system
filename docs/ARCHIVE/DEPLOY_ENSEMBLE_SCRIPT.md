# Deploy Ensemble Download Script to Production

## Quick Deploy Instructions

### 1. Copy files to production server

```bash
# From your local machine
scp download_ensemble_data.py root@41.139.151.242:/root/
scp .env root@41.139.151.242:/root/
scp ENSEMBLE_DATA_GUIDE.md root@41.139.151.242:/root/
```

### 2. SSH into production server

```bash
ssh root@41.139.151.242
```

### 3. Test network connectivity first

```bash
# Quick port check
timeout 5 bash -c "echo > /dev/tcp/<FTP_HOST>/22" && echo "✓ Port 22 reachable" || echo "✗ Port blocked"
```

### 4. Install dependencies (if needed)

```bash
pip install paramiko
```

### 5. Test the script

```bash
cd /root

# List available files on server (doesn't download)
python3 download_ensemble_data.py --list-only

# If listing works, download today's data
python3 download_ensemble_data.py

# Or download last 7 days
python3 download_ensemble_data.py --days 7
```

### 6. Check downloaded files

```bash
ls -lh ./data/ensemble/
ls -lh ./data/ensemble/20251105/  # Check today's date folder
```

### 7. Verify CSV content

```bash
# Check first Zone file
head -20 ./data/ensemble/20251105/Zone1_20251105.csv
```

Expected format:
```csv
GRIDCODE,DATE,RIVERDEPTH,STREAMFLOW
42,20251105,1.5,25.3
43,20251105,2.1,30.5
```

## Alternative: Run inside Docker container

If the script needs to run regularly, you can:

### Option A: Run from backend container

```bash
# Copy script into backend container
sudo docker cp download_ensemble_data.py floodwatch_backend_staging:/app/

# Run inside container
sudo docker exec -it floodwatch_backend_staging bash
cd /app
python download_ensemble_data.py --days 7

# Files will be in /app/data/ensemble/
ls -la /app/data/ensemble/
```

### Option B: Create a scheduled cron job

```bash
# On production server, create cron job
crontab -e

# Add line to download ensemble data daily at 6 AM
0 6 * * * cd /root && /usr/bin/python3 download_ensemble_data.py --days 1 >> /var/log/ensemble_download.log 2>&1
```

## Troubleshooting

### Connection refused or timeout

If you get connection errors:

1. **Check from production server**: The script may work from the production server but not your local machine
2. **VPN required**: You might need to be on a specific VPN
3. **IP whitelist**: Contact the GeoSFM team to whitelist the production server IP
4. **Firewall**: Port 22 might be blocked by firewall rules

### Wrong credentials

If you get "Authentication failed":

1. Double-check credentials in `.env` file
2. Verify with GeoSFM team that credentials are still valid
3. Check if password has special characters that need escaping

### No files found

If script says "No Zone files found":

1. Run with `--list-only` to see what dates are available
2. The server might not have data for recent dates
3. Try a specific date you know exists: `--date 20251020`

### Permission denied when saving files

```bash
# Create directory with proper permissions
mkdir -p ./data/ensemble
chmod 755 ./data/ensemble
```

## Next Steps After Download Works

Once you can successfully download files:

### 1. Create processing script

Process the CSV files and merge with control points:

```bash
# This will parse CSVs and save to database
python manage.py sync_ensemble_to_db --days 7
```

### 2. Set up automated sync

```bash
# Cron job to download and process daily
0 6 * * * cd /root && python3 download_ensemble_data.py --days 1 && docker exec floodwatch_backend_staging python manage.py sync_ensemble_to_db --local
```

### 3. Verify data in database

```bash
# Check how many ensemble forecast records exist
sudo docker exec -it floodwatch_backend_staging python manage.py shell

>>> from Impact.models import GeoSFMForecastGeoJSON
>>> GeoSFMForecastGeoJSON.objects.count()
>>> GeoSFMForecastGeoJSON.objects.latest('data_date')
```

## File Locations on Production

- Script: `/root/download_ensemble_data.py`
- Downloaded data: `/root/data/ensemble/YYYYMMDD/`
- Logs: `/var/log/ensemble_download.log` (if using cron)
- Environment: `/root/.env`

## Success Indicators

You'll know it's working when you see:

```
============================================================
🌊 Ensemble Forecast Data Downloader
============================================================
SFTP Server: <FTP_HOST>:22
Remote Path: /ftproot/output/Combined
Local Path:  ./data/ensemble
============================================================

📅 Will download 1 date(s):
   - 2025-11-05 (20251105)

🔌 Connecting to SFTP server <FTP_HOST>:22...
✅ Connected successfully!

============================================================
📋 Listing Available Files
============================================================
📁 Listing all files in /ftproot/output/Combined...

✓ Found 36 Zone CSV files:
  📅 2025-11-05 (20251105):
     - Zone1_20251105.csv (Zone 1, 0.45 MB)
     - Zone2_20251105.csv (Zone 2, 0.38 MB)
     - Zone3_20251105.csv (Zone 3, 0.52 MB)
     - Zone4_20251105.csv (Zone 4, 0.41 MB)
     - Zone5_20251105.csv (Zone 5, 0.49 MB)
     - Zone6_20251105.csv (Zone 6, 0.44 MB)
```

## Contact

If connection issues persist, contact the GeoSFM team to:
1. Verify credentials are still valid
2. Confirm the production server IP is whitelisted
3. Check if there are any network/firewall restrictions
