# Ensemble Forecast Data Integration Guide

This guide explains how to download and work with ensemble forecast data from the GeoSFM SFTP server.

## Overview

- **Data Source**: GeoSFM SFTP Server at `41.215.21.156`
- **Remote Path**: `/ftproot/output/Combined` (appears as `D:\ftproot\output\Combined` in Windows)
- **File Format**: CSV files named `Zone1_YYYYMMDD.csv`, `Zone2_YYYYMMDD.csv`, etc.
- **Data Type**: Ensemble hydrological forecast (river depth and streamflow)

## Configuration

The SFTP credentials are configured in your `.env` file:

```bash
# Ensemble Data Configuration (GeoSFM) - via SFTP
ENSEMBLE_SFTP_HOST=41.215.21.156
ENSEMBLE_SFTP_PORT=22
ENSEMBLE_SFTP_USERNAME=geosfm
ENSEMBLE_SFTP_PASSWORD=icpac#254
# Remote path on SFTP server (shown as D:\ftproot\output\Combined in Windows explorer)
ENSEMBLE_REMOTE_PATH=/ftproot/output/Combined
# Local cache directory for downloaded ensemble files
ENSEMBLE_LOCAL_CACHE=/app/ensemble_cache
```

## Download Script: `download_ensemble_data.py`

A standalone Python script to download Zone CSV files from the SFTP server.

### Prerequisites

```bash
pip install paramiko
```

### Usage

#### 1. List available files on the server:

```bash
python download_ensemble_data.py --list-only
```

This will show you all available Zone CSV files grouped by date.

#### 2. Download today's data:

```bash
python download_ensemble_data.py
```

Downloads Zone files for today only to `./data/ensemble/YYYYMMDD/`

#### 3. Download a specific date:

```bash
python download_ensemble_data.py --date 20251022
```

Downloads Zone files for October 22, 2025.

#### 4. Download last 7 days:

```bash
python download_ensemble_data.py --days 7
```

Downloads Zone files for the last 7 days.

#### 5. Specify custom output directory:

```bash
python download_ensemble_data.py --days 7 --output-dir /path/to/data
```

## Zone CSV File Format

Each Zone file contains forecast data for a specific geographic zone:

```csv
GRIDCODE,DATE,RIVERDEPTH,STREAMFLOW
42,20251022,1.5,25.3
43,20251022,2.1,30.5
```

- **GRIDCODE**: Unique identifier matching `EnsembleControlPoint.gridcode` in database
- **DATE**: Forecast date in YYYYMMDD format
- **RIVERDEPTH**: River depth forecast value (meters)
- **STREAMFLOW**: Streamflow forecast value (m³/s)

## Directory Structure

After downloading, files are organized by date:

```
./data/ensemble/
├── 20251020/
│   ├── Zone1_20251020.csv
│   ├── Zone2_20251020.csv
│   ├── Zone3_20251020.csv
│   ├── Zone4_20251020.csv
│   ├── Zone5_20251020.csv
│   └── Zone6_20251020.csv
├── 20251021/
│   ├── Zone1_20251021.csv
│   └── ...
└── 20251022/
    └── ...
```

## Next Steps

### 1. Process and Merge Data (To Be Implemented)

Create a script to:
1. Parse downloaded Zone CSV files
2. Match GRIDCODE values with `EnsembleControlPoint` geometries in the database
3. Create GeoJSON FeatureCollection with forecast values
4. Either:
   - Store in `GeoSFMForecastGeoJSON` model for ensemble data
   - Or merge with deterministic forecasts in `MergedDeterministicGeoJSON`

### 2. Database Models

**EnsembleControlPoint** (already exists):
- Contains reference points with GRIDCODE, coordinates, zone info
- Used for spatial matching with forecast data

**GeoSFMForecastGeoJSON** (already exists):
- Stores merged ensemble forecast GeoJSON per date
- Fields: `data_date`, `geojson_data`, `feature_count`, `matched_count`, `zones_processed`
- Includes statistics: `riverdepth_min/max`, `streamflow_min/max`

### 3. Django Management Command (To Be Created)

A management command `sync_ensemble_to_db` will:
1. Download Zone CSV files from SFTP (or use local cache)
2. Parse CSV data and map to GRIDCODE
3. Merge with EnsembleControlPoint geometries
4. Save to GeoSFMForecastGeoJSON model

```bash
python manage.py sync_ensemble_to_db --days 7
python manage.py sync_ensemble_to_db --date 2025-10-22
python manage.py sync_ensemble_to_db --local  # Use cached files
```

## Troubleshooting

### Connection Issues

If you get "Unable to connect" errors:

1. **Check network access**: The SFTP server may only be accessible from certain networks or VPNs
2. **Verify credentials**: Ensure `.env` has correct credentials
3. **Test connectivity**: Try using an SFTP client like FileZilla first
4. **Firewall**: Port 22 (SSH/SFTP) may be blocked

### No Files Found

If the script says "No Zone files found for date X":

1. Run with `--list-only` to see what dates are available
2. The server may not have data for recent dates yet
3. Try downloading data for a date you know exists

### File Format Issues

If CSV parsing fails:

1. Check the CSV file structure matches expected format
2. Look for encoding issues (should be UTF-8)
3. Verify column names: `GRIDCODE`, `DATE`, `RIVERDEPTH`, `STREAMFLOW`

## Example Workflow

```bash
# 1. List available files on server
python download_ensemble_data.py --list-only

# 2. Download specific date after confirming it exists
python download_ensemble_data.py --date 20251020

# 3. Check downloaded files
ls -lh ./data/ensemble/20251020/

# 4. Process and load to database (when implemented)
python manage.py sync_ensemble_to_db --date 2025-10-20
```

## Integration with FloodWatch

Once ensemble data is in the database:

1. **FastAPI Endpoints**: Add endpoints to serve ensemble forecast GeoJSON
2. **Frontend Display**: Show ensemble forecasts alongside deterministic forecasts
3. **Comparison View**: Allow users to compare ensemble vs deterministic predictions
4. **Uncertainty Visualization**: Display ensemble spread/confidence intervals

## File Locations

- Download script: `./download_ensemble_data.py`
- Downloaded data: `./data/ensemble/YYYYMMDD/`
- Management command: `./backend/Impact/management/commands/sync_ensemble_to_db.py`
- Environment config: `./.env`

## References

- EnsembleControlPoint model: `backend/Impact/models.py:373`
- GeoSFMForecastGeoJSON model: `backend/Impact/models.py:303`
- SFTP sync pattern: `backend/scripts/sftp_sync.py`
- Similar sync command: `backend/Impact/management/commands/sync_floodproofs_to_db.py`
