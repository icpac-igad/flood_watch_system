# Ensemble Data Download - Status Report

## Summary

Tested multiple methods to automatically download ensemble forecast data from the Windows server (41.215.21.156). All automated methods failed due to credential/access limitations.

## Server Information

- **Host**: 41.215.21.156
- **OS**: Windows
- **Data Location**: `D:\ftproot\output\Combined`
- **File Pattern**: `Zone1_YYYYMMDD.csv`, `Zone2_YYYYMMDD.csv`, etc. (6 zones per date)

## Available Credentials

- **Username**: geosfm
- **Password**: icpac#254
- **Access Level**: RDP/VM login only (not FTP or SMB admin access)

## Methods Tested

### 1. SFTP (SSH File Transfer) ❌
- **Port**: 22
- **Status**: CLOSED
- **Result**: Connection refused
- **Reason**: Server doesn't run SSH/SFTP service

```bash
nmap -p 22 41.215.21.156
# Output: 22/tcp closed ssh
```

### 2. FTP (File Transfer Protocol) ❌
- **Port**: 21
- **Status**: OPEN
- **Result**: 530 Login incorrect
- **Reason**: geosfm/icpac#254 credentials don't work for FTP

```bash
ftp 41.215.21.156
# Connected, but login fails with "530 Login incorrect"
```

**Error**:
```
ftp> user geosfm
331 Password required for geosfm.
Password: [icpac#254]
530 Login incorrect.
ftp: Login failed
```

### 3. SMB Administrative Shares (C$, D$, etc.) ❌
- **Protocol**: SMB/CIFS
- **Available Shares**: ADMIN$, C$, D$, E$, F$, IPC$
- **Result**: NT_STATUS_ACCESS_DENIED
- **Reason**: Current credentials don't have administrative access

```bash
smbclient -L //41.215.21.156 -U "geosfm%icpac#254"
# Shows shares: C$, D$, E$, F$

smbclient //41.215.21.156/D$ -U "geosfm%icpac#254" -c "ls"
# Error: NT_STATUS_ACCESS_DENIED
```

### 4. RDP (Remote Desktop Protocol) ✅
- **Port**: 3389
- **Tool**: Remmina
- **Result**: SUCCESS
- **Access**: Full Windows desktop access

```bash
# User confirmed: "remina is connecting using same password"
# Can access D:\ftproot\output\Combined via Windows Explorer
```

## Scripts Created

### Automated Download Scripts (Non-functional)

1. **download_ensemble_data.py** (FTP version)
   - Uses ftplib
   - Fails at authentication (530 error)
   - Needs valid FTP credentials

2. **download_ensemble_smb.py** (Mount version)
   - Uses mount.cifs
   - Requires sudo access
   - Would fail with ACCESS_DENIED anyway

3. **download_ensemble_smbclient.py** (SMBClient version)
   - Uses smbclient command
   - No sudo required
   - Fails with NT_STATUS_ACCESS_DENIED

### Testing Scripts

4. **test_ftp_connection.py**
   - Quick FTP credential tester
   - Confirms FTP authentication fails

## Working Solutions

### Option 1: Manual Download via RDP (Current Best Option)

**Steps**:
1. Connect to Windows server via Remmina:
   - Host: 41.215.21.156
   - Protocol: RDP
   - Username: geosfm
   - Password: icpac#254

2. Navigate to: `D:\ftproot\output\Combined`

3. Transfer files using one of these methods:
   - **Drag and Drop**: If Remmina folder sharing enabled
   - **Shared Folder**: Configure Remmina to share `./data/ensemble/` directory
   - **Copy/Paste**: Copy files in Windows, paste in local Linux

**Detailed Guide**: See [ENSEMBLE_MANUAL_DOWNLOAD.md](ENSEMBLE_MANUAL_DOWNLOAD.md)

### Option 2: Request Proper Credentials

Contact the GeoSFM team or server administrator to obtain:

**For FTP Access**:
- Valid FTP username and password
- FTP should already be running on port 21

**For SMB Access**:
- Either:
  - Administrative credentials for D$ share access, OR
  - Set up a regular SMB share (e.g., `//41.215.21.156/ensemble`) that geosfm can access

### Option 3: Set Up Automated Sync from Windows VM

Create a PowerShell script on the Windows VM to push files to the production server:

**On Windows VM** (`D:\sync_ensemble_data.ps1`):
```powershell
# Install PuTTY's pscp.exe first
$sourcePath = "D:\ftproot\output\Combined"
$destServer = "197.254.1.10"
$destPath = "/root/data/ensemble"

# Get today's files
$today = Get-Date -Format "yyyyMMdd"
$files = Get-ChildItem "$sourcePath\Zone*_$today.csv"

# Copy via SCP
foreach ($file in $files) {
    Write-Host "Uploading $($file.Name)..."
    pscp.exe -pw "your_ssh_password" $file.FullName "root@${destServer}:${destPath}/"
}
```

**Schedule with Task Scheduler**:
- Run daily at 6 AM
- Automatically syncs new ensemble data

## Recommendations

### Immediate Action (Today)

Use **Option 1 (Manual RDP Download)**:

1. Connect via Remmina to 41.215.21.156
2. Set up shared folder in Remmina settings pointing to `./data/ensemble/`
3. Copy today's Zone CSV files (Zone1_20251105.csv through Zone6_20251105.csv)
4. Verify files locally:
   ```bash
   ls -lh ./data/ensemble/20251105/
   head -20 ./data/ensemble/20251105/Zone1_20251105.csv
   ```

### Short-term Solution (This Week)

Contact GeoSFM team to:
1. Verify FTP credentials or get new ones
2. OR configure a regular SMB share accessible by geosfm user
3. Confirm the production server (197.254.1.10) is IP whitelisted

### Long-term Solution (Production)

Once credentials are obtained:
1. Deploy working download script to production server
2. Set up cron job for daily downloads:
   ```bash
   0 6 * * * cd /root && python3 download_ensemble_data.py --days 1
   ```
3. Integrate with Django management command:
   ```bash
   python manage.py sync_ensemble_to_db --days 1
   ```

## Next Steps

1. **Download sample data manually** via RDP to test the data processing pipeline
2. **Request proper credentials** from GeoSFM team
3. **Test automated download** once credentials obtained
4. **Deploy to production** with cron scheduling

## File Locations

- **Download Scripts**: `./download_ensemble_*.py`
- **Documentation**: `./ENSEMBLE_*.md`
- **Local Data Cache**: `./data/ensemble/YYYYMMDD/`
- **Environment Config**: `.env` (ENSEMBLE_* variables)

## Expected File Structure

After successful download:
```
./data/ensemble/
├── 20251103/
│   ├── Zone1_20251103.csv
│   ├── Zone2_20251103.csv
│   ├── Zone3_20251103.csv
│   ├── Zone4_20251103.csv
│   ├── Zone5_20251103.csv
│   └── Zone6_20251103.csv
├── 20251104/
│   └── ...
└── 20251105/
    ├── Zone1_20251105.csv
    ├── Zone2_20251105.csv
    ├── Zone3_20251105.csv
    ├── Zone4_20251105.csv
    ├── Zone5_20251105.csv
    └── Zone6_20251105.csv
```

Each CSV format:
```csv
GRIDCODE,DATE,RIVERDEPTH,STREAMFLOW
42,20251105,1.5,25.3
43,20251105,2.1,30.5
...
```

## Contact

For access issues, contact:
- **GeoSFM Team**: Request FTP or SMB credentials
- **Server Admin**: IP whitelist production server
- **Network Team**: Check firewall rules if needed

---

**Status**: Waiting for proper FTP/SMB credentials or using manual RDP download as interim solution.

**Last Updated**: 2025-11-05
