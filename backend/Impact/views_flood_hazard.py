"""
Flood Hazard Map Views
Handles dynamic date-based raster serving through MapServer
"""
import os
import glob
import io
import subprocess
from datetime import datetime, date, timedelta
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import logging

try:
    from PIL import Image
    import numpy as np
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False

logger = logging.getLogger(__name__)

# Base path for flood hazard rasters
FLOOD_HAZARD_BASE_PATH = "/backend/Impact_forecast"

@require_http_methods(["GET"])
def get_available_flood_dates(request):
    """
    Returns available dates for flood hazard maps
    """
    try:
        available_dates = []
        
        # Scan the directory structure for available dates
        year_dirs = glob.glob(os.path.join(FLOOD_HAZARD_BASE_PATH, "20*"))
        
        for year_dir in sorted(year_dirs):
            year = os.path.basename(year_dir)
            month_dirs = glob.glob(os.path.join(year_dir, "*"))
            
            for month_dir in sorted(month_dirs):
                month = os.path.basename(month_dir)
                day_dirs = glob.glob(os.path.join(month_dir, "*"))
                
                for day_dir in sorted(day_dirs):
                    day = os.path.basename(day_dir)
                    
                    # Check if flood hazard file exists
                    hazard_files = glob.glob(os.path.join(day_dir, "00", "0000", "flood_hazard_map_*.tif"))
                    if hazard_files:
                        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        try:
                            # Validate date format
                            datetime.strptime(date_str, "%Y-%m-%d")
                            available_dates.append(date_str)
                        except ValueError:
                            continue
        
        return JsonResponse({
            'dates': sorted(available_dates),
            'count': len(available_dates)
        })
        
    except Exception as e:
        logger.error(f"Error getting flood hazard dates: {str(e)}")
        return JsonResponse({'error': 'Failed to retrieve available dates'}, status=500)

@require_http_methods(["GET"])
def get_flood_hazard_metadata(request, date_str):
    """
    Returns metadata for a specific flood hazard map
    """
    try:
        # Validate date format
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Build file path
        file_path = _build_flood_hazard_path(date_obj)
        
        if not os.path.exists(file_path):
            raise Http404(f"Flood hazard map not found for date {date_str}")
        
        # Get file stats
        stat = os.stat(file_path)
        
        metadata = {
            'date': date_str,
            'file_path': file_path,
            'file_size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'mapserver_layer': 'flood_hazard_map',
            'mapcache_tileset': 'flood_hazard_tiles',
            'wms_url': f"{request.scheme}://{request.get_host()}/mapserver/wms",
            'wmts_url': f"{request.scheme}://{request.get_host()}/mapcache/wmts",
        }
        
        return JsonResponse(metadata)
        
    except Http404:
        return JsonResponse({'error': f'Flood hazard map not found for date {date_str}'}, status=404)
    except Exception as e:
        logger.error(f"Error getting flood hazard metadata for {date_str}: {str(e)}")
        return JsonResponse({'error': 'Failed to retrieve metadata'}, status=500)

@require_http_methods(["GET"])
def get_latest_flood_hazard(request):
    """
    Returns metadata for the most recent flood hazard map
    """
    try:
        # Get all available dates
        dates_response = get_available_flood_dates(request)
        dates_data = dates_response.content
        
        if dates_response.status_code != 200:
            return dates_response
            
        import json
        dates = json.loads(dates_data)['dates']
        
        if not dates:
            return JsonResponse({'error': 'No flood hazard maps available'}, status=404)
        
        # Get the latest date
        latest_date = dates[-1]
        
        # Return metadata for latest date
        return get_flood_hazard_metadata(request, latest_date)
        
    except Exception as e:
        logger.error(f"Error getting latest flood hazard: {str(e)}")
        return JsonResponse({'error': 'Failed to retrieve latest flood hazard'}, status=500)

@require_http_methods(["GET"])
def proxy_mapserver_wms(request, date_str):
    """
    Proxy WMS requests to MapServer with dynamic date substitution
    """
    try:
        # Validate date
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return HttpResponse('Invalid date format', status=400)
        
        # Check if file exists
        file_path = _build_flood_hazard_path(date_obj)
        if not os.path.exists(file_path):
            return HttpResponse('Flood hazard map not found', status=404)
        
        # Build MapServer URL with substitution
        import urllib.parse
        
        # Create a temporary mapfile with the specific date
        mapfile_content = _create_dynamic_mapfile(date_obj, file_path)
        
        # For now, return the mapfile content for debugging
        # In production, this would proxy to MapServer
        return HttpResponse(mapfile_content, content_type='text/plain')
        
    except Exception as e:
        logger.error(f"Error proxying WMS for {date_str}: {str(e)}")
        return HttpResponse('WMS proxy error', status=500)

def _build_flood_hazard_path(date_obj):
    """
    Build the file path for a flood hazard map based on date
    """
    timestamp = date_obj.strftime("%Y%m%d0000")
    year = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    day = date_obj.strftime("%d")
    
    filename = f"flood_hazard_map_floodproofs_{timestamp}.tif"
    
    return os.path.join(
        FLOOD_HAZARD_BASE_PATH,
        year, month, day, "00", "0000",
        filename
    )

def _create_dynamic_mapfile(date_obj, file_path):
    """
    Create a dynamic mapfile with the specific file path
    """
    timestamp = date_obj.strftime("%Y%m%d0000")
    
    mapfile = f"""MAP
  NAME "FloodHazard_{timestamp}"
  EXTENT -180 -90 180 90
  UNITS DD
  SIZE 800 600
  IMAGECOLOR 255 255 255
  IMAGETYPE PNG
  
  PROJECTION
    "init=epsg:4326"
  END
  
  WEB
    METADATA
      "wms_title" "Flood Hazard Map {date_obj.strftime('%Y-%m-%d')}"
      "wms_onlineresource" "http://localhost:8093/cgi-bin/mapserv"
      "wms_srs" "EPSG:4326 EPSG:3857"
      "wms_enable_request" "*"
      "wms_format" "image/png"
    END
  END
  
  LAYER
    NAME "flood_hazard_{timestamp}"
    STATUS ON
    TYPE RASTER
    DATA "{file_path}"
    
    PROJECTION
      "init=epsg:4326"
    END
    
    METADATA
      "wms_title" "Flood Hazard {date_obj.strftime('%Y-%m-%d')}"
      "wms_srs" "EPSG:4326 EPSG:3857"
      "wms_format" "image/png"
      "wms_transparent" "true"
    END
    
    PROCESSING "BANDS=1"
    PROCESSING "SCALE=AUTO"
    PROCESSING "NULLVALUE=0"
    
    CLASSITEM "[pixel]"
    
    CLASS
      NAME "No Flood Risk"
      EXPRESSION ([pixel] = 0)
      STYLE
        COLOR 255 255 255
        OPACITY 0
      END
    END
    
    CLASS
      NAME "Low Risk"
      EXPRESSION ([pixel] > 0 AND [pixel] <= 0.25)
      STYLE
        COLOR 255 255 0
        OPACITY 60
      END
    END
    
    CLASS
      NAME "Medium Risk"
      EXPRESSION ([pixel] > 0.25 AND [pixel] <= 0.5)
      STYLE
        COLOR 255 165 0
        OPACITY 70
      END
    END
    
    CLASS
      NAME "High Risk"
      EXPRESSION ([pixel] > 0.5 AND [pixel] <= 0.75)
      STYLE
        COLOR 255 69 0
        OPACITY 80
      END
    END
    
    CLASS
      NAME "Very High Risk"
      EXPRESSION ([pixel] > 0.75)
      STYLE
        COLOR 255 0 0
        OPACITY 90
      END
    END
  END
END"""
    
    return mapfile