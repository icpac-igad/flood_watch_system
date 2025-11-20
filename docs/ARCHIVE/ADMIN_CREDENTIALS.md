# FloodWatch Admin Credentials

## Django Admin Access

**URL**: http://localhost:8090/admin/

---

## Superuser Account (Full Access)

- **Username**: `admin`
- **Password**: `floodwatch2024`
- **Email**: admin@floodwatch.icpac.net
- **Role**: Full system administrator with all permissions

---

## Member State Admin Accounts

### Kenya
- **Username**: `kenya_admin`
- **Password**: `memberstate2024`
- **Email**: kenya@floodwatch.icpac.net
- **Role**: Member state administrator for Kenya

### Ethiopia
- **Username**: `ethiopia_admin`
- **Password**: `memberstate2024`
- **Email**: ethiopia@floodwatch.icpac.net
- **Role**: Member state administrator for Ethiopia

### Uganda
- **Username**: `uganda_admin`
- **Password**: `memberstate2024`
- **Email**: uganda@floodwatch.icpac.net
- **Role**: Member state administrator for Uganda

### Tanzania
- **Username**: `tanzania_admin`
- **Password**: `memberstate2024`
- **Email**: tanzania@floodwatch.icpac.net
- **Role**: Member state administrator for Tanzania

### Sudan
- **Username**: `sudan_admin`
- **Password**: `memberstate2024`
- **Email**: sudan@floodwatch.icpac.net
- **Role**: Member state administrator for Sudan

---

## ICPAC/RTMWA Admin Account

- **Username**: `icpac_admin`
- **Password**: `icpac2024`
- **Email**: icpac@floodwatch.icpac.net
- **Role**: ICPAC/RTMWA administrator for final report approval

---

## Sample Data Created

### Station Report Approvals (5 records)

1. **KE001** - Kenya Meteorological Department
   - Status: ✅ Approved (both member state and ICPAC)
   - POC: Dr. Jane Kamau

2. **ET002** - Ethiopian Meteorological Institute
   - Status: ⏳ Pending ICPAC review (member state approved)
   - POC: Dr. Abebe Tadesse

3. **UG003** - Uganda National Meteorological Authority
   - Status: ⏳ Pending (awaiting member state approval)
   - POC: Ms. Sarah Nakato

4. **TZ004** - Tanzania Meteorological Authority
   - Status: ⚠️ Changes Requested (by member state)
   - POC: Mr. John Mwangi

5. **SD005** - Sudan Meteorological Authority
   - Status: ⚠️ Changes Requested (by ICPAC)
   - POC: Dr. Ahmed Ibrahim

---

## Admin Features Available

### Station Report Approvals
- **URL**: http://localhost:8090/admin/Impact/stationreportapproval/
- View and manage two-stage approval workflow
- Color-coded status badges
- Filter by approval status
- Search by station ID, POC name, reviewer name
- Date hierarchy for tracking

### Saved Reports
- **URL**: http://localhost:8090/admin/Impact/savedreport/
- Manage saved flood reports
- Filter by status, forecast date, country, basin
- View report details and risk assessments

### Merged Deterministic GeoJSON Data
- **URL**: http://localhost:8090/admin/Impact/mergeddeterministicgeojson/
- View forecast data records (365 days loaded)
- Date hierarchy navigation
- Feature count and file statistics

---

## Two-Stage Approval Workflow

### Stage 1: Member State Approval
1. Member state POC reviews station data
2. Updates status to: approved, pending, changes_requested, or rejected
3. Adds comments explaining decision
4. Timestamp recorded when approved

### Stage 2: ICPAC/RTMWA Final Approval
1. ICPAC reviewer assesses member state approved reports
2. Updates ICPAC status to: approved, pending, changes_requested, or rejected
3. Adds final review comments
4. Timestamp recorded when approved

### Final Status Calculation
- **Approved**: Both stages approved
- **Pending**: Either stage pending
- **Changes Requested**: Either stage requests changes
- **Rejected**: Either stage rejected

---

## Security Notes

⚠️ **IMPORTANT**: These are development/testing credentials.

For production deployment:
- Change all default passwords immediately
- Use strong, unique passwords for each account
- Enable two-factor authentication
- Implement role-based access control
- Use HTTPS for all admin access
- Review Django security settings in settings.py

---

## Quick Start

1. Navigate to: http://localhost:8090/admin/
2. Login with the `admin` superuser account
3. Explore the sample station report approvals
4. Test the approval workflow by updating statuses
5. View the color-coded status badges

---

*Generated: 2025-10-23*
*FloodWatch System v1.0*
