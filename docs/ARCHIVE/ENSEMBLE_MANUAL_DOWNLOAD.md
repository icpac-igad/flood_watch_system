# Manual Ensemble Data Download Guide

Since FTP credentials are not available, here's how to download ensemble data manually via RDP.

## Option 1: Manual Download via Remmina (RDP)

### Step 1: Connect to the Server
1. Open Remmina
2. Connect to `41.215.21.156` using RDP
3. Login with:
   - Username: (your Windows username)
   - Password: `icpac#254`

### Step 2: Navigate to Data Directory
1. Once connected, open File Explorer
2. Navigate to: `D:\ftproot\output\Combined`
3. You'll see files like:
   - `Zone1_20251105.csv`
   - `Zone2_20251105.csv`
   - `Zone3_20251105.csv`
   - etc.

### Step 3: Copy Files
Select the Zone files you need and copy them to your local machine:

**Method A: Drag and Drop**
- If Remmina has folder sharing enabled, drag files to your local folder

**Method B: Shared Folder**
1. In Remmina, set up a shared folder (Settings > Basic > Share folder)
2. Point it to `./data/ensemble/` on your local machine
3. Copy files from `D:\ftproot\output\Combined` to the shared folder

**Method C: Copy and Paste**
1. Select files in Windows Explorer
2. Copy (Ctrl+C)
3. On your local machine, paste in `./data/ensemble/`

## Option 2: Use SCP from Production Server

If the production server can reach the Windows VM, use SCP/rsync:

```bash
# On production server (197.254.1.10)
# Install sshpass if needed
sudo apt-get install sshpass

# Download files (if SSH is enabled on Windows VM)
sshpass -p 'icpac#254' scp -r username@41.215.21.156:/ftproot/output/Combined/*.csv ./data/ensemble/
```

## Option 3: Mount SMB Share

If Windows file sharing is enabled, you can mount the share:

```bash
# Install cifs-utils
sudo apt-get install cifs-utils

# Create mount point
mkdir -p ~/ensemble_mount

# Mount the Windows share
sudo mount -t cifs //41.215.21.156/ftproot/output/Combined ~/ensemble_mount \
  -o username=geosfm,password=icpac#254

# Copy files
cp ~/ensemble_mount/Zone*.csv ./data/ensemble/20251105/

# Unmount when done
sudo umount ~/ensemble_mount
```

## Option 4: Use PowerShell Script on Windows VM

Create this script on the Windows VM to copy files automatically:

```powershell
# ensemble_sync.ps1
# Run this on the Windows VM

$sourcePath = "D:\ftproot\output\Combined"
$destinationServer = "197.254.1.10"
$destinationPath = "/root/data/ensemble"

# Get today's files
$today = Get-Date -Format "yyyyMMdd"
$files = Get-ChildItem "$sourcePath\Zone*_$today.csv"

# Copy via SCP (requires pscp.exe from PuTTY)
foreach ($file in $files) {
    Write-Host "Uploading $($file.Name)..."
    pscp.exe -pw "your_ssh_password" $file.FullName "root@${destinationServer}:${destinationPath}/"
}
```

## Expected Files Per Date

For each date (e.g., `20251105`), you should have 6 files:
```
Zone1_20251105.csv
Zone2_20251105.csv
Zone3_20251105.csv
Zone4_20251105.csv
Zone5_20251105.csv
Zone6_20251105.csv
```

## CSV File Format

Each file contains:
```csv
GRIDCODE,DATE,RIVERDEPTH,STREAMFLOW
42,20251105,1.5,25.3
43,20251105,2.1,30.5
...
```

## Directory Structure

Organize downloaded files by date:
```
./data/ensemble/
├── 20251103/
│   ├── Zone1_20251103.csv
│   ├── Zone2_20251103.csv
│   └── ...
├── 20251104/
│   └── ...
└── 20251105/
    └── ...
```

## Next Steps After Download

Once you have the CSV files locally:

1. **Verify the files:**
   ```bash
   ls -lh ./data/ensemble/20251105/
   head -20 ./data/ensemble/20251105/Zone1_20251105.csv
   ```

2. **Process and load to database** (when ready):
   ```bash
   python manage.py sync_ensemble_to_db --local --date 2025-11-05
   ```

3. **Set up automated download:**
   - Schedule the PowerShell script on Windows VM (Task Scheduler)
   - Or manually download weekly/daily as needed

## Troubleshooting

### Can't access D:\ftproot folder
- Check if you have permission
- Try running as Administrator
- Contact server admin for access

### Files not present
- Check if data generation process is running
- Look for files with recent dates
- Contact GeoSFM team about data availability

### Large file sizes
- Zone CSV files are typically 0.5-2 MB each
- Total per day: ~6-12 MB (6 zones)
- Can compress before transfer if needed
