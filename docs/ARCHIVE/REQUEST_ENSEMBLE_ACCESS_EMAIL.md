# Email Draft: Request for Ensemble Data Access Credentials

---

**To:** IT Team, Supervisor
**Subject:** Request for FTP/SMB Credentials - Ensemble Forecast Data Access (41.215.21.156)

---

Dear IT Team and Supervisor,

I am working on integrating ensemble forecast data from the GeoSFM server into our FloodWatch application. The data is located on the Windows server at **41.215.21.156** in the directory `D:\ftproot\output\Combined`.

## Current Situation

I have RDP access to the server using the credentials:
- **Username:** geosfm
- **Password:** icpac#254
- **Access:** Windows desktop via Remmina (working)

However, I need automated access to download Zone CSV files (Zone1_YYYYMMDD.csv through Zone6_YYYYMMDD.csv) daily for our production system. I have tested multiple methods, and here are the results:

## Access Methods Tested

### 1. FTP (Port 21) - ❌ Failed
- **Status:** FTP service is running and accessible
- **Issue:** Current credentials fail with "530 Login incorrect"
- **Test Command:** `ftp 41.215.21.156` (connection succeeds, login fails)

### 2. SMB/CIFS File Shares - ❌ Failed
- **Status:** Administrative shares (C$, D$, E$) are visible
- **Issue:** "NT_STATUS_ACCESS_DENIED" with current credentials
- **Test Command:** `smbclient //41.215.21.156/D$ -U geosfm` (access denied)

### 3. SFTP/SSH (Port 22) - ❌ Not Available
- **Status:** Port 22 is closed
- **Issue:** Server doesn't run SSH service

### 4. RDP (Port 3389) - ✅ Working
- **Status:** Can manually access files through Windows desktop
- **Issue:** Not suitable for automated daily downloads in production

## What I Need

To implement automated daily downloads for our production FloodWatch system, I need **one** of the following:

### Option A: FTP Credentials (Preferred)
- Valid FTP username and password for accessing `/ftproot/output/Combined`
- The FTP service is already running on port 21
- This would allow automated downloads using our prepared Python scripts

### Option B: SMB Share Access (Alternative)
Either:
- Administrative credentials that can access the D$ share, **OR**
- A regular SMB share configured (e.g., `//41.215.21.156/ensemble`) that the `geosfm` user can access

### Option C: IP Whitelisting
If different credentials are required, please also ensure that our production server **197.254.1.10** is whitelisted/allowed to access the Windows server.

## Use Case

We need to:
1. Download 6 Zone CSV files daily (approximately 3-6 MB total)
2. Process the data and integrate it with our FloodWatch database
3. Display ensemble forecast data on our map viewer for flood prediction

## Current Workaround

I can manually download files via RDP, but this is not sustainable for production deployment. I have prepared automated download scripts that will work immediately once proper credentials are provided.

## Scripts Prepared

I have created and tested the following scripts (ready to deploy):
- `download_ensemble_data.py` - FTP-based automated download
- `download_ensemble_smbclient.py` - SMB-based automated download
- `test_ftp_connection.py` - Credential testing utility

## Request Summary

**Please provide:**
1. Valid FTP credentials for automated access to `/ftproot/output/Combined`, **OR**
2. SMB share credentials/configuration for file access
3. Confirmation that production server IP (197.254.1.10) is whitelisted

## Timeline

This is needed for our production deployment. Once credentials are provided, I can:
- Test and verify access within 1 hour
- Deploy automated daily sync to production same day
- Complete ensemble data integration into FloodWatch

## Contact Information

Please reply with the credentials or let me know if you need any additional information. I'm happy to coordinate a quick call if that would be easier.

Thank you for your assistance!

Best regards,
[Your Name]

---

## Technical Details (for IT Team)

**Server Information:**
- Host: 41.215.21.156
- OS: Windows
- Data Location: `D:\ftproot\output\Combined`
- File Pattern: `Zone1_YYYYMMDD.csv`, `Zone2_YYYYMMDD.csv`, etc.
- Required Access: Read-only to `/ftproot/output/Combined` directory

**Current Test Results:**
```bash
# FTP Test
$ ftp 41.215.21.156
Connected to 41.215.21.156.
220 Microsoft FTP Service
Name: geosfm
331 Password required for geosfm.
Password: [icpac#254]
530 Login incorrect.
ftp: Login failed

# SMB Test
$ smbclient -L //41.215.21.156 -U geosfm
# Shows: ADMIN$, C$, D$, E$, F$, IPC$

$ smbclient //41.215.21.156/D$ -U geosfm
tree connect failed: NT_STATUS_ACCESS_DENIED

# SFTP Test
$ nmap -p 22 41.215.21.156
22/tcp closed ssh
```

**Our Production Environment:**
- Server: 197.254.1.10
- OS: Linux (Ubuntu/Debian)
- Application: FloodWatch (Django + PostgreSQL + PostGIS)
- Download Schedule: Daily at 6 AM (via cron)

