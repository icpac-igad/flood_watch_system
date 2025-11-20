"""
Hazards (merged alerts) API utilities
Reads available dates from merged_alerts/daily and exposes simple endpoints
"""
import os
import glob
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In docker-compose we mount ./merged_alerts to /app/merged_alerts
HAZARDS_BASE = os.path.abspath(os.path.join(BASE_DIR, '..', 'merged_alerts', 'daily'))


def _list_hazard_dates():
    dates = []
    try:
        # Prefer a provided available_dates.txt if present
        dates_file = os.path.join(HAZARDS_BASE, 'available_dates.txt')
        if os.path.exists(dates_file):
            with open(dates_file, 'r') as f:
                for line in f:
                    s = line.strip()
                    if len(s) == 8 and s.isdigit():
                        dates.append(s)
        else:
            # Fallback: glob the tifs and extract dates
            for tif in glob.glob(os.path.join(HAZARDS_BASE, 'hmc_alert_daily_*.tif')):
                name = os.path.basename(tif)
                # hmc_alert_daily_YYYYMMDD.tif
                parts = name.split('_')
                if len(parts) >= 4:
                    ymd = parts[3].split('.')[0]
                    if len(ymd) == 8 and ymd.isdigit():
                        dates.append(ymd)
        # Unique and sort ascending
        dates = sorted(list({d for d in dates}))
    except Exception:
        dates = []
    return dates


@require_http_methods(["GET"])
def hazards_available_dates(request):
    dates_ymd = _list_hazard_dates()
    # Also provide ISO format for convenience
    dates_iso = [f"{d[0:4]}-{d[4:6]}-{d[6:8]}" for d in dates_ymd]
    return JsonResponse({
        'dates': dates_iso,
        'dates_ymd': dates_ymd,
        'count': len(dates_ymd)
    })


@require_http_methods(["GET"])
def hazards_latest(request):
    dates_ymd = _list_hazard_dates()
    if not dates_ymd:
        return JsonResponse({'error': 'No hazard rasters available'}, status=404)
    latest_ymd = dates_ymd[-1]
    latest_iso = f"{latest_ymd[0:4]}-{latest_ymd[4:6]}-{latest_ymd[6:8]}"
    return JsonResponse({
        'latest': latest_iso,
        'latest_ymd': latest_ymd
    })

