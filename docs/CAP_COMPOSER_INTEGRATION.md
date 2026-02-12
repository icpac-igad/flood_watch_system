# CAP Composer Integration Guide

## Overview

This document describes all steps needed to integrate the **CAP (Common Alerting Protocol) Composer** into FloodWatch. CAP Composer (`cap-composer` by WMO-RAF) is a Wagtail application that handles alert authoring, CAP 1.2 XML serialization, and distribution (RSS, GeoJSON, webhooks, MQTT).

The integration lets forecasters generate CAP flood alerts directly from their expert assessments in the FloodWatch map viewer.

**Architecture decision**: CAP Composer runs **inside** the existing `eafw_cms` Django process (not as a separate service), since it's a Wagtail app that uses `Page` models, `BaseSiteSetting`, and `wagtail_hooks`.

---

## Prerequisites

| Item | Current | Required |
|------|---------|----------|
| Wagtail | `>=6.3.6,<6.4` | `>=7.0,<7.1` |
| cap-composer source | Available at `hazard_watch/cap-composer/capcomposer/` | Same |
| Redis | Not deployed | Needed for Celery (Module 7 only) |

---

## Module 1: Wagtail Upgrade + CAP App Installation

**Risk**: HIGH -- Wagtail 6->7 has breaking changes. Test thoroughly.

### Step 1.1: Fix `get_full_url` deprecation in geomanager

`wagtail.api.v2.utils.get_full_url` was **removed** in Wagtail 7. The `geomanager` package imports it in 11+ files.

**Create compat function** in `eafw_cms/geomanager/geomanager/utils/__init__.py`:

```python
from urllib.parse import urljoin
from django.conf import settings

def get_full_url(request, path):
    """
    Compatibility shim replacing wagtail.api.v2.utils.get_full_url
    which was removed in Wagtail 7.
    """
    if not path:
        path = ""
    cms_base_url = getattr(settings, "CMS_BASE_URL", None)
    if cms_base_url:
        if path and not path.startswith("/"):
            path = "/" + path
        return urljoin(cms_base_url, path)
    if request:
        return request.build_absolute_uri(path)
    return path
```

**Replace imports** in all these files (change `from wagtail.api.v2.utils import get_full_url` to `from geomanager.utils import get_full_url`):

```
geomanager/wagtail_hooks.py
geomanager/views/vector_tile.py
geomanager/views/vector_file.py
geomanager/views/tile_gl.py
geomanager/views/raster_file.py
geomanager/views/core.py
geomanager/models/boundary.py
geomanager/models/geomanager_settings.py
geomanager/models/vector_file.py
geomanager/models/raster_file.py
geomanager/models/tile_base.py
geomanager/models/wms.py
```

Also update `geomanager/serializers/core.py` to use the shared function:
```python
# Replace the local _get_full_url with:
from geomanager.utils import get_full_url as _get_full_url
# Delete the inline _get_full_url function definition
```

### Step 1.2: Update geomanager version constraint

In `eafw_cms/geomanager/pyproject.toml`, change:
```toml
# Before:
"wagtail>=6.3.6,<6.4",
# After:
"wagtail>=6.3.6",
```

### Step 1.3: Update CMS dependencies

In `eafw_cms/pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing deps ...
    "wagtail>=7.0,<7.1",          # WAS: "wagtail>=6.3.6,<6.4"
    # CAP Composer dependencies (add these):
    "capcomposer",
    "wagtail-modelchooser>=4.0.1",
    "wagtail-newsletter==0.2.2",
    "paho-mqtt>=2.1.0",
    "xmltodict>=0.14.2",
    "pdf2image>=1.17.0",
    "lxml>=5.4.0",
    "signxml>=4.0.3",
    "loguru>=0.7.3",
    "feedparser>=6.0.11",
    "staticmap==0.5.7",
    "capvalidator==0.1.0.dev4",
    "python-magic",
    "mailchimp-marketing==3.0.80",
    "mrml>=0.2",
    "django-celery-beat",
]

[tool.uv.sources]
geomanager = { path = "./geomanager" }
capcomposer = { path = "../hazard_watch/cap-composer/capcomposer" }   # ADD THIS
```

### Step 1.4: Add cap-composer to Python path

In `eafw_cms/geomanagerweb/settings/base.py`, after the GEOMANAGER_PATH block:

```python
CAP_COMPOSER_PATH = '/path/to/hazard_watch/cap-composer/capcomposer/src'
if CAP_COMPOSER_PATH not in sys.path:
    sys.path.insert(0, CAP_COMPOSER_PATH)
```

> **Note**: In Docker, this path should be set via env var or relative to the project root.

### Step 1.5: Add CAP apps to INSTALLED_APPS

In `eafw_cms/geomanagerweb/settings/base.py`, add to the beginning of `INSTALLED_APPS` (after `"geomanager"`):

```python
INSTALLED_APPS = [
    "home",
    "geomanager",
    # CAP Composer apps
    "capcomposer.capeditor",
    "capcomposer.cap",
    "wagtail_modelchooser",
    "wagtail_newsletter",
    "django_celery_beat",
    # ... rest of existing apps ...
]
```

### Step 1.6: Add CAP URL patterns

In `eafw_cms/geomanagerweb/urls.py`, add before the Wagtail catch-all:

```python
urlpatterns = [
    # ... existing patterns ...
    path("", include("geomanager.urls")),
    path("", include("django_nextjs.urls")),
    # CAP Composer URLs (RSS, GeoJSON, XML feeds)
    path("", include("capcomposer.cap.urls")),
]
```

This registers these endpoints (built into cap-composer):
- `GET /api/cap/rss.xml` -- RSS feed of CAP alerts
- `GET /api/cap/alerts.geojson` -- GeoJSON of active alerts
- `GET /api/cap/<uuid>.xml` -- Individual CAP XML alert
- `GET /home-map-alerts/` -- Map alerts for homepage
- `GET /latest-active-alert/` -- Latest active alert

### Step 1.7: Install & verify

```bash
cd eafw_cms
uv sync
python manage.py check          # Should pass with no errors
python manage.py migrate         # Creates CAP tables in cms schema
# Test Wagtail admin loads, existing pages render, geomanager panels work
```

### Known Wagtail 7 breaking changes to watch for

| Change | Impact | Fix |
|--------|--------|-----|
| `wagtail.api.v2.utils.get_full_url` removed | geomanager (11 files) | Compat shim (Step 1.1) |
| `wagtail.contrib.forms` may be deprecated | Listed in INSTALLED_APPS | Remove if not using form submissions |
| StreamField `use_json_field` required | Already set in geomanager | No action needed |

---

## Module 2: CAP Configuration Seed Data

**Goal**: Populate CAP settings so alert creation is possible from Wagtail admin.

### Step 2.1: Create CapAlertListPage migration

Create `eafw_cms/home/migrations/0037_create_cap_alert_list_page.py`:

```python
from django.db import migrations

def create_cap_alert_list_page(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Page = apps.get_model("wagtailcore", "Page")
    CapAlertListPage = apps.get_model("cap", "CapAlertListPage")

    # Get or create content type
    ct, _ = ContentType.objects.get_or_create(
        app_label="cap", model="capalertlistpage"
    )

    # Get root page
    root_page = Page.objects.filter(depth=1).first()
    if not root_page:
        return

    # Check if already exists
    if CapAlertListPage.objects.exists():
        return

    # Create as child of root
    list_page = CapAlertListPage(
        title="CAP Alerts",
        slug="cap-alerts",
        heading="CAP Flood Alerts",
        content_type=ct,
        path=root_page.path + "0005",  # Adjust based on existing children
        depth=root_page.depth + 1,
    )
    root_page.add_child(instance=list_page)
    list_page.save_revision().publish()

def reverse(apps, schema_editor):
    CapAlertListPage = apps.get_model("cap", "CapAlertListPage")
    CapAlertListPage.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ("home", "0036_update_alert_thresholds"),
        ("cap", "__first__"),
        ("wagtailcore", "__latest__"),
    ]
    operations = [
        migrations.RunPython(create_cap_alert_list_page, reverse),
    ]
```

### Step 2.2: Create CAP Settings seed migration

Create `eafw_cms/home/migrations/0038_seed_cap_settings.py`:

```python
from django.db import migrations

GHA_COUNTRIES = [
    "Burundi", "Djibouti", "Eritrea", "Ethiopia", "Kenya",
    "Rwanda", "Somalia", "South Sudan", "Sudan", "Tanzania", "Uganda",
]

LANGUAGES = [
    ("en", "English"),
    ("sw", "Swahili"),
    ("ar", "Arabic"),
    ("am", "Amharic"),
    ("fr", "French"),
    ("so", "Somali"),
]

HAZARD_TYPES = [
    {"event": "Flood", "category": "Met", "icon": "flood"},
    {"event": "Flash Flood", "category": "Met", "icon": "flash-flood"},
]

def seed_cap_settings(apps, schema_editor):
    Site = apps.get_model("wagtailcore", "Site")
    CapSetting = apps.get_model("capeditor", "CapSetting")
    HazardEventTypes = apps.get_model("capeditor", "HazardEventType")  # Check actual model name
    AlertLanguage = apps.get_model("capeditor", "AlertLanguage")
    PredefinedAlertArea = apps.get_model("capeditor", "PredefinedAlertArea")

    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        return

    setting, created = CapSetting.objects.get_or_create(site=site)
    if not created:
        return

    setting.sender = "info@icpac.net"
    setting.sender_name = "ICPAC"
    setting.save()

    # Add hazard types
    for i, hazard in enumerate(HAZARD_TYPES):
        HazardEventTypes.objects.create(
            cap_setting=setting,
            event=hazard["event"],
            category=hazard["category"],
            icon=hazard.get("icon", ""),
            sort_order=i,
        )

    # Add languages
    for i, (code, name) in enumerate(LANGUAGES):
        AlertLanguage.objects.create(
            cap_setting=setting,
            code=code,
            name=name,
            sort_order=i,
        )

    # Add predefined areas from gha.admin0
    # NOTE: Query actual admin0 geometries from DB
    # PredefinedAlertArea requires MultiPolygonField geometry
    from django.db import connection
    with connection.cursor() as cursor:
        for i, country in enumerate(GHA_COUNTRIES):
            cursor.execute(
                "SELECT ST_AsText(geom) FROM gha.admin0 WHERE name_0 = %s LIMIT 1",
                [country]
            )
            row = cursor.fetchone()
            if row:
                from django.contrib.gis.geos import GEOSGeometry
                geom = GEOSGeometry(row[0])
                if geom.geom_type == 'Polygon':
                    from django.contrib.gis.geos import MultiPolygon
                    geom = MultiPolygon(geom)
                PredefinedAlertArea.objects.create(
                    cap_setting=setting,
                    name=country,
                    geom=geom,
                    sort_order=i,
                )

class Migration(migrations.Migration):
    dependencies = [
        ("home", "0037_create_cap_alert_list_page"),
        ("capeditor", "__first__"),
    ]
    operations = [
        migrations.RunPython(seed_cap_settings, migrations.RunPython.noop),
    ]
```

> **Important**: The exact model names (`HazardEventType` vs `HazardEventTypes`, `PredefinedAlertArea`, field names like `cap_setting` vs `setting`) must be verified against the actual cap-composer models before running. Check `capcomposer/src/capcomposer/capeditor/cap_settings.py` for the actual `related_name` and model class names.

### Verification

- CAP Settings visible in Wagtail admin -> Settings -> CAP Settings
- Can manually create a test CAP alert through Wagtail admin
- CAP alert list page accessible at `/cap-alerts/`

---

## Module 3: Assessment-to-CAP Data Bridge

**Goal**: Python module that transforms FloodWatch assessment data into CAP alert drafts.

### Step 3.1: Create the package structure

```
eafw_cms/home/cap_bridge/
    __init__.py
    mapper.py
    gatherer.py
    area_builder.py
    creator.py
```

### Step 3.2: mapper.py -- Risk level to CAP field mapping

```python
RISK_TO_CAP = {
    "emergency": {"severity": "Extreme",  "urgency": "Immediate", "certainty": "Observed"},
    "alarm":     {"severity": "Severe",   "urgency": "Expected",  "certainty": "Likely"},
    "warning":   {"severity": "Moderate", "urgency": "Future",    "certainty": "Possible"},
    "normal":    {"severity": "Minor",    "urgency": "Past",      "certainty": "Unlikely"},
}

def get_cap_fields(risk_level: str) -> dict:
    """Map FloodWatch risk level to CAP severity/urgency/certainty."""
    return RISK_TO_CAP.get(risk_level.lower(), RISK_TO_CAP["normal"])
```

### Step 3.3: gatherer.py -- Query assessment data

Queries `gha.expert_assessments` and `gha.district_risk_levels` tables. Returns a dataclass with all data needed to build a CAP alert.

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from django.db import connection

@dataclass
class DistrictRisk:
    district_name: str
    gid_2: str
    risk_level: str  # "warning", "alarm", "emergency"

@dataclass
class AssessmentForCAP:
    assessment_id: int
    forecast_date: datetime
    country_name: str
    country_code: str
    expert_comment: str
    overall_risk: str
    district_risks: List[DistrictRisk]

def get_assessment_for_cap(assessment_id: int) -> Optional[AssessmentForCAP]:
    """Query DB for assessment data needed to create a CAP alert."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, forecast_date, country_name, country_code,
                   expert_comment, overall_risk_level
            FROM gha.expert_assessments
            WHERE id = %s
        """, [assessment_id])
        row = cursor.fetchone()
        if not row:
            return None

        cursor.execute("""
            SELECT district_name, gid_2, risk_level
            FROM gha.district_risk_levels
            WHERE assessment_id = %s AND risk_level != 'normal'
        """, [assessment_id])
        districts = [
            DistrictRisk(district_name=r[0], gid_2=r[1], risk_level=r[2])
            for r in cursor.fetchall()
        ]

    return AssessmentForCAP(
        assessment_id=row[0],
        forecast_date=row[1],
        country_name=row[2],
        country_code=row[3],
        expert_comment=row[4],
        overall_risk=row[5],
        district_risks=districts,
    )
```

> **Note**: Verify actual column names in `gha.expert_assessments` and `gha.district_risk_levels` tables before implementing. These are placeholder names based on the plan.

### Step 3.4: area_builder.py -- Convert district geometries to CAP areas

```python
from django.db import connection

def build_cap_areas(district_risks):
    """Build CAP area dicts from district risk data with geometries from gha.admin2."""
    areas = []
    for dr in district_risks:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name_2, ST_AsGeoJSON(geom)
                FROM gha.admin2
                WHERE gid_2 = %s
            """, [dr.gid_2])
            row = cursor.fetchone()
            if row:
                import json
                areas.append({
                    "areaDesc": row[0],
                    "polygon": json.loads(row[1]),
                })
    return areas
```

### Step 3.5: creator.py -- Orchestrator

```python
from datetime import timedelta
from django.utils import timezone
from .gatherer import get_assessment_for_cap
from .mapper import get_cap_fields
from .area_builder import build_cap_areas

def create_cap_draft_from_assessment(assessment_id, expires_hours=48):
    """Create a draft CAP alert from a saved expert assessment."""
    assessment = get_assessment_for_cap(assessment_id)
    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    cap_fields = get_cap_fields(assessment.overall_risk)
    areas = build_cap_areas(assessment.district_risks)

    now = timezone.now()
    alert_data = {
        "sender": "info@icpac.net",
        "sent": now.isoformat(),
        "status": "Draft",
        "msgType": "Alert",
        "scope": "Public",
        "info": [{
            "language": "en",
            "category": "Met",
            "event": "Flood",
            "responseType": ["Monitor"],
            "urgency": cap_fields["urgency"],
            "severity": cap_fields["severity"],
            "certainty": cap_fields["certainty"],
            "effective": now.isoformat(),
            "onset": assessment.forecast_date.isoformat(),
            "expires": (now + timedelta(hours=expires_hours)).isoformat(),
            "senderName": "ICPAC",
            "headline": f"Flood {assessment.overall_risk.title()} - {assessment.country_name}",
            "description": assessment.expert_comment or f"Flood {assessment.overall_risk} level for {assessment.country_name}",
            "instruction": "Monitor water levels and follow local authority guidance.",
            "area": areas,
        }],
    }

    # Import cap-composer's utility
    from capcomposer.cap.utils import create_draft_alert_from_alert_data
    cap_page = create_draft_alert_from_alert_data(alert_data)
    return cap_page
```

### Key reference: `create_draft_alert_from_alert_data()` expected format

Located at `hazard_watch/cap-composer/capcomposer/src/capcomposer/cap/utils.py:185`

**Function signature**:
```python
def create_draft_alert_from_alert_data(
    alert_data,
    request=None,
    update_event_list=False,
    update_contact_list=False,
    submit_for_moderation=False
)
```

**Returns**: `CapAlertPage` (draft, unpublished) or `None` if no `CapAlertListPage` exists.

**Full alert_data dict structure**:
```python
{
    "sender": str,                    # Email/identifier
    "sent": str,                      # ISO datetime
    "status": str,                    # "Draft"|"Actual"|"Test"|"Exercise"|"System"
    "msgType": str,                   # "Alert"|"Update"|"Cancel"
    "scope": str,                     # "Public"|"Restricted"|"Private"
    "restriction": str,               # Required if scope="Restricted"
    "note": str,                      # Optional note
    "info": [
        {
            "language": str,          # ISO 639-1 code
            "category": str,          # "Geo"|"Met"|"Safety" etc.
            "event": str,             # "Flood", "Flash Flood"
            "responseType": [str],    # ["Monitor", "Evacuate", etc.]
            "urgency": str,           # "Immediate"|"Expected"|"Future"|"Past"|"Unknown"
            "severity": str,          # "Extreme"|"Severe"|"Moderate"|"Minor"|"Unknown"
            "certainty": str,         # "Observed"|"Likely"|"Possible"|"Unlikely"|"Unknown"
            "effective": str,         # ISO datetime
            "onset": str,             # ISO datetime
            "expires": str,           # ISO datetime
            "senderName": str,
            "headline": str,
            "description": str,
            "instruction": str,
            "contact": str,
            "audience": str,
            "eventCode": [{"valueName": str, "value": str}],
            "parameter": [{"valueName": str, "value": str}],
            "resource": [{"uri": str, "resourceDesc": str}],
            "area": [
                {
                    "areaDesc": str,
                    "polygon": <GeoJSON geometry>,
                    "geocode": {"valueName": str, "value": str},
                    "circle": [str],
                }
            ]
        }
    ]
}
```

---

## Module 4: CAP API Endpoints + Nginx Routing

### Step 4.1: Django view for CAP draft creation

In `eafw_cms/geomanagerweb/api.py`, add:

```python
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

@method_decorator(csrf_exempt, name="dispatch")
class CAPDraftCreateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            assessment_id = data.get("assessment_id")
            expires_hours = data.get("expires_hours", 48)

            if not assessment_id:
                return JsonResponse({"success": False, "message": "assessment_id required"}, status=400)

            from home.cap_bridge.creator import create_cap_draft_from_assessment
            cap_page = create_cap_draft_from_assessment(assessment_id, expires_hours)

            if not cap_page:
                return JsonResponse({"success": False, "message": "Failed to create draft"}, status=500)

            return JsonResponse({
                "success": True,
                "cap_alert_id": cap_page.id,
                "edit_url": f"/admin/pages/{cap_page.id}/edit/",
                "message": "CAP alert draft created",
            })
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
```

### Step 4.2: Register Django URL

In `eafw_cms/geomanagerweb/urls.py`, add:

```python
from geomanagerweb.api import CAPDraftCreateView

urlpatterns = [
    # ... existing patterns ...
    path("cms-api/cap/create-draft/", CAPDraftCreateView.as_view(), name="cap_create_draft"),
]
```

### Step 4.3: FastAPI CAP router

Create `eafw_api/src/eafw_api/routers/v1/cap.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/cap", tags=["CAP Alerts"])

class CapDraftRequest(BaseModel):
    assessment_id: int
    expires_hours: int = 48

class CapDraftResponse(BaseModel):
    success: bool
    cap_alert_id: int | None = None
    edit_url: str | None = None
    message: str

@router.post("/draft", response_model=CapDraftResponse)
async def create_cap_draft(request: CapDraftRequest):
    """Proxy to Django CMS to create a CAP alert draft."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://eafw_cms:8000/cms-api/cap/create-draft/",
            json=request.model_dump(),
            timeout=30.0,
        )
    return resp.json()

@router.get("/alerts")
async def get_cap_alerts():
    """Proxy to cap-composer's GeoJSON endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://eafw_cms:8000/api/cap/alerts.geojson",
            timeout=10.0,
        )
    return resp.json()
```

Register in `eafw_api/src/eafw_api/main.py`:
```python
from eafw_api.routers.v1.cap import router as cap_router
app.include_router(cap_router, prefix="/api/v1")
```

### Step 4.4: Nginx routing

Add to both `eafw_docker/nginx/nginx.local.conf` and `nginx.staging.conf`:

```nginx
# CAP XML/RSS/GeoJSON feeds (served by Django/cap-composer)
location /api/cap/ {
    proxy_pass http://eafw_cms:8000/api/cap/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### API contracts

```
POST /api/v1/cap/draft
Request:  { "assessment_id": 123, "expires_hours": 48 }
Response: { "success": true, "cap_alert_id": 456, "edit_url": "/admin/pages/456/edit/", "message": "..." }

GET /api/v1/cap/alerts
Response: GeoJSON FeatureCollection of active CAP alerts

GET /api/cap/rss.xml        -> RSS feed (direct from cap-composer)
GET /api/cap/alerts.geojson -> GeoJSON (direct from cap-composer)
GET /api/cap/<uuid>.xml     -> Individual CAP XML (direct from cap-composer)
```

---

## Module 5: CAP Alerts Display Widget (Frontend)

### Step 5.1: Create widget files

```
eafw_mapviewer/src/components/flood-analysis/widgets/cap-alerts/
    index.jsx           # Main widget
    cap-alert-list.jsx  # Scrollable alert cards
    cap-alert-detail.jsx # Expanded view
    styles.scss
```

### Step 5.2: CAP service

Create or update `eafw_mapviewer/src/services/cap.js`:

```javascript
import request from "utils/request";

export const getActiveAlerts = (params = {}) =>
  request.get("/api/v1/cap/alerts", { params });

export const createCapDraft = (assessmentId, options = {}) =>
  request.post("/api/v1/cap/draft", {
    assessment_id: assessmentId,
    expires_hours: options.expiresHours || 48,
  });
```

### Step 5.3: Widget component

```jsx
// index.jsx
import React, { useState, useEffect } from "react";
import { getActiveAlerts } from "services/cap";
import "./styles.scss";

const SEVERITY_COLORS = {
  Extreme: "#d32f2f",
  Severe: "#f57c00",
  Moderate: "#fbc02d",
  Minor: "#4caf50",
};

const CapAlertsWidget = ({ forecastDate, selectedCountry }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getActiveAlerts({ country: selectedCountry, date: forecastDate })
      .then((data) => setAlerts(data?.features || []))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false));
  }, [forecastDate, selectedCountry]);

  if (loading) return <div className="cap-alerts-loading">Loading alerts...</div>;
  if (!alerts.length) return <div className="cap-alerts-empty">No active CAP alerts</div>;

  return (
    <div className="cap-alerts-widget">
      <h4>Active CAP Alerts ({alerts.length})</h4>
      {alerts.map((alert) => (
        <div
          key={alert.properties?.identifier}
          className="cap-alert-card"
          style={{ borderLeftColor: SEVERITY_COLORS[alert.properties?.severity] }}
        >
          <strong>{alert.properties?.headline}</strong>
          <span className="severity">{alert.properties?.severity}</span>
          <span className="expires">Expires: {alert.properties?.expires}</span>
        </div>
      ))}
    </div>
  );
};

export default CapAlertsWidget;
```

### Step 5.4: Register in widgets container

In `eafw_mapviewer/src/components/flood-analysis/widgets/index.jsx`, import and render:

```jsx
import CapAlertsWidget from "./cap-alerts";

// In the render, between ExpertAssessment and ActionButtons:
<CapAlertsWidget
  forecastDate={params?.forecast_date}
  selectedCountry={selectedCountry?.code}
/>
```

---

## Module 6: "Generate CAP Alert" Button

### Step 6.1: Create button component

Create `eafw_mapviewer/src/components/flood-analysis/widgets/expert-assessment/cap-draft-button.jsx`:

```jsx
import React, { useState } from "react";
import { createCapDraft } from "services/cap";

const CapDraftButton = ({ assessmentId, disabled }) => {
  const [state, setState] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);

  const handleClick = async () => {
    setState("loading");
    try {
      const data = await createCapDraft(assessmentId);
      setResult(data);
      setState("success");
    } catch (err) {
      setResult({ message: err.message });
      setState("error");
    }
  };

  if (state === "success" && result) {
    return (
      <div className="cap-draft-success">
        Draft created.{" "}
        <a href={result.edit_url} target="_blank" rel="noopener noreferrer">
          Edit in CMS Admin &rarr;
        </a>
      </div>
    );
  }

  return (
    <button
      className="cap-draft-button"
      onClick={handleClick}
      disabled={disabled || state === "loading"}
    >
      {state === "loading" ? "Creating..." : "Generate CAP Alert Draft"}
    </button>
  );
};

export default CapDraftButton;
```

### Step 6.2: Add to expert assessment widget

In `eafw_mapviewer/src/components/flood-analysis/widgets/expert-assessment/index.jsx`, after assessment save success:

```jsx
import CapDraftButton from "./cap-draft-button";

// After save success state:
{savedAssessmentId && (
  <CapDraftButton assessmentId={savedAssessmentId} />
)}
```

### UX flow

1. Forecaster completes and saves expert assessment
2. "Generate CAP Alert Draft" button appears
3. Click -> loading state -> API call to `/api/v1/cap/draft`
4. Success -> "Draft created. [Edit in CMS Admin ->]" link
5. Forecaster opens Wagtail admin, reviews/edits, publishes

---

## Module 7: Distribution Pipeline (Celery + Redis)

### Step 7.1: Create Celery app

Create `eafw_cms/geomanagerweb/celery.py`:

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geomanagerweb.settings.dev")

app = Celery("geomanagerweb")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### Step 7.2: Import celery app

In `eafw_cms/geomanagerweb/__init__.py`:

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

### Step 7.3: Enable Celery settings

In `eafw_cms/geomanagerweb/settings/base.py`, uncomment:

```python
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", "redis://eafw_redis:6379/0")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", "redis://eafw_redis:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
```

### Step 7.4: Add Docker services

In `docker-compose.local.yml`:

```yaml
eafw_redis:
  image: redis:7-alpine
  container_name: eafw-redis
  restart: unless-stopped
  volumes:
    - redis_data:/data

eafw_celery_worker:
  image: eafw-cms
  container_name: eafw-celery-worker
  command: celery -A geomanagerweb worker -l info
  depends_on:
    - eafw_redis
    - eafw_db
  env_file:
    - eafw_cms/.env
  volumes:
    - ./eafw_cms:/app
    - media_data:/app/media

eafw_celery_beat:
  image: eafw-cms
  container_name: eafw-celery-beat
  command: celery -A geomanagerweb beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  depends_on:
    - eafw_redis
    - eafw_db
  env_file:
    - eafw_cms/.env
  volumes:
    - ./eafw_cms:/app

volumes:
  redis_data:
```

### What this enables (built into cap-composer)

When a CAP alert is published (status=Actual, scope=Public), the `page_published` signal triggers:
- `handle_publish_alert_to_mqtt.delay()` -- publish to configured MQTT brokers
- `handle_publish_alert_to_webhook.delay()` -- fire configured webhooks
- `handle_generate_multimedia.delay()` -- generate PNG map + PDF preview

Webhook/MQTT brokers are configured through Wagtail admin UI (already built into cap-composer).

---

## Implementation Order

| Phase | Module | Effort | Depends on |
|-------|--------|--------|-----------|
| **1** | Module 1: Wagtail Upgrade | High risk, medium effort | Nothing |
| **2** | Module 2: Seed Data | Low effort | Module 1 |
| **3** | Module 3: Data Bridge | Medium effort | Module 2 |
| **3** | Module 4: API + Nginx | Medium effort | Module 2 |
| **3** | Module 5: Display Widget | Medium effort | Module 2 |
| **3** | Module 7: Distribution | Medium effort | Module 2 |
| **4** | Module 6: Generate Button | Low effort | Modules 3 + 4 |

Modules 3, 4, 5, 7 can be developed **in parallel** after Module 2.

---

## Key Files Reference

| Purpose | Path |
|---------|------|
| CMS dependencies | `eafw_cms/pyproject.toml` |
| CMS settings | `eafw_cms/geomanagerweb/settings/base.py` |
| CMS URLs | `eafw_cms/geomanagerweb/urls.py` |
| CMS API views | `eafw_cms/geomanagerweb/api.py` |
| Home models | `eafw_cms/home/models.py` |
| Home migrations | `eafw_cms/home/migrations/` (next: 0037) |
| Geomanager package | `eafw_cms/geomanager/` |
| Geomanager pyproject | `eafw_cms/geomanager/pyproject.toml` |
| cap-composer source | `hazard_watch/cap-composer/capcomposer/src/capcomposer/` |
| `create_draft_alert_from_alert_data()` | `hazard_watch/cap-composer/capcomposer/src/capcomposer/cap/utils.py:185` |
| CAP models | `hazard_watch/cap-composer/capcomposer/src/capcomposer/cap/models.py` |
| CAP settings model | `hazard_watch/cap-composer/capcomposer/src/capcomposer/capeditor/cap_settings.py` |
| CAP constants | `hazard_watch/cap-composer/capcomposer/src/capcomposer/capeditor/constants.py` |
| CAP URL patterns | `hazard_watch/cap-composer/capcomposer/src/capcomposer/cap/urls.py` |
| Expert assessment widget | `eafw_mapviewer/src/components/flood-analysis/widgets/expert-assessment/index.jsx` |
| Widgets container | `eafw_mapviewer/src/components/flood-analysis/widgets/index.jsx` |
| FastAPI routers | `eafw_api/src/eafw_api/routers/v1/` |
| FastAPI main | `eafw_api/src/eafw_api/main.py` |
| Nginx local config | `eafw_docker/nginx/nginx.local.conf` |
| Nginx staging config | `eafw_docker/nginx/nginx.staging.conf` |
| Docker compose | `docker-compose.local.yml` |

---

## Verification Checklist

### After Module 1
- [ ] `python manage.py check` passes
- [ ] `python manage.py migrate` creates CAP tables
- [ ] Wagtail admin loads without errors
- [ ] Existing pages (HomePage, SituationReportPage) still render
- [ ] `geomanager` admin panels still work

### After Module 2
- [ ] CAP Settings visible in Wagtail admin -> Settings -> CAP Settings
- [ ] Can manually create a test CAP alert through admin
- [ ] Alert list page accessible at `/cap-alerts/`

### After Module 3
- [ ] Unit tests for mapper pass
- [ ] `create_cap_draft_from_assessment(id)` creates a draft CapAlertPage

### After Module 4
- [ ] `curl /api/cap/alerts.geojson` returns valid GeoJSON
- [ ] `curl /api/cap/rss.xml` returns valid RSS
- [ ] `POST /api/v1/cap/draft` creates a draft in Wagtail

### After Module 5
- [ ] Widget renders "No active alerts" when empty
- [ ] Widget shows alert cards when alerts exist

### After Module 6
- [ ] Button appears after assessment save
- [ ] Creates draft with correct pre-filled data
- [ ] Edit link opens Wagtail page editor

### After Module 7
- [ ] Publishing an alert triggers webhook (test with webhook.site)
- [ ] PNG/PDF generated in media directory
