"""
Views for layer date availability endpoints
Provides API endpoints to check which dates have available data for each layer
"""

import os
import re
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

# Map layer IDs to their data directories
# Note: Paths are absolute in the container
LAYER_DATA_PATHS = {
    # Inundation layers - recursive search in year/month/day subdirectories
    'fp_inundation': '/mapserver_data/inundation/',
    'fp_discharge': '/mapserver_data/hazards/',
    'wrf_discharge': '/mapserver_data/wrf/',
    'flood_hazard': '/mapserver_data/inundation/',
    'Alerts': '/mapserver_data/hazards/',
    'wrf_alerts': '/mapserver_data/wrf/',

    # IBEW layers
    'ibew_v1_affected_population': '/mapserver_data/ibew/',
    'ibew_v1_affected_cropland': '/mapserver_data/ibew/',
    'ibew_v1_affected_livestock': '/mapserver_data/ibew/',
    'ibew_v2_affected_population': '/mapserver_data/ibew/',
    'ibew_v2_affected_cropland': '/mapserver_data/ibew/',
    'ibew_v2_affected_livestock': '/mapserver_data/ibew/',

    # Real-time raster data
    'latest_inundation': '/mapserver_data/inundation/',
    'latest_alerts': '/mapserver_data/hazards/',
}

# Layer groups that share the same date availability
LAYER_GROUPS = {
    'inundationMaps': ['fp_inundation', 'fp_discharge', 'wrf_discharge'],
    'impactLayers': [
        'ibew_v1_affected_population',
        'ibew_v1_affected_cropland',
        'ibew_v1_affected_livestock',
        'ibew_v2_affected_population',
        'ibew_v2_affected_cropland',
        'ibew_v2_affected_livestock',
    ],
    'realTimeRaster': ['latest_inundation', 'latest_alerts'],
}


def extract_date_from_filename(filename, patterns=None):
    """
    Extract date from filename using various patterns

    Args:
        filename: The filename to parse
        patterns: List of regex patterns to try. If None, uses default patterns.

    Returns:
        datetime object if date found, None otherwise
    """
    if patterns is None:
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{8})',  # YYYYMMDD
            r'(\d{4})_(\d{2})_(\d{2})',  # YYYY_MM_DD
        ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                if len(match.groups()) == 1:
                    date_str = match.group(1)
                    # Try different formats
                    for fmt in ['%Y-%m-%d', '%Y%m%d']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                elif len(match.groups()) == 3:
                    # YYYY_MM_DD format
                    year, month, day = match.groups()
                    return datetime(int(year), int(month), int(day))
            except (ValueError, TypeError):
                continue

    return None


def scan_directory_for_dates(directory_path):
    """
    Scan a directory recursively for files and extract dates from filenames

    Args:
        directory_path: Path to directory to scan

    Returns:
        List of date strings in YYYY-MM-DD format, sorted
    """
    dates = set()

    if not os.path.exists(directory_path):
        logger.warning(f"Directory not found: {directory_path}")
        return []

    try:
        # Walk through all subdirectories recursively
        for root, dirs, files in os.walk(directory_path):
            for filename in files:
                # Skip non-data files
                if not (filename.endswith(('.tif', '.tiff', '.shp', '.geojson', '.json'))):
                    continue

                # Extract date from filename
                date_obj = extract_date_from_filename(filename)

                if date_obj:
                    dates.add(date_obj.strftime('%Y-%m-%d'))

    except Exception as e:
        logger.error(f"Error scanning directory {directory_path}: {e}")

    return sorted(list(dates))


def generate_sample_dates(days=30):
    """
    Generate sample dates for development/testing

    Args:
        days: Number of days to generate

    Returns:
        List of date strings
    """
    today = datetime.now()
    dates = []

    for i in range(days):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))

    return sorted(dates)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_layer_available_dates(request, layer_id):
    """
    Get available dates for a specific layer

    GET /api/layers/<layer_id>/available-dates/

    Returns:
        {
            "layer_id": "fp_inundation",
            "dates": ["2024-09-01", "2024-09-02", ...],
            "count": 30,
            "first_date": "2024-09-01",
            "last_date": "2024-09-30"
        }
    """
    # Check if layer exists
    if layer_id not in LAYER_DATA_PATHS:
        return Response(
            {
                'error': f'Unknown layer: {layer_id}',
                'available_layers': list(LAYER_DATA_PATHS.keys())
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # Get data path for layer
    data_path = LAYER_DATA_PATHS[layer_id]

    # Scan directory for dates
    dates = scan_directory_for_dates(data_path)

    # Fallback to sample dates in development
    if not dates and os.getenv('DJANGO_ENV') == 'development':
        logger.info(f"Using sample dates for layer {layer_id}")
        dates = generate_sample_dates(30)

    # Build response
    response_data = {
        'layer_id': layer_id,
        'dates': dates,
        'count': len(dates),
    }

    if dates:
        response_data['first_date'] = dates[0]
        response_data['last_date'] = dates[-1]

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_layer_group_available_dates(request, group_id):
    """
    Get available dates for a layer group (union of all layers in group)

    GET /api/layer-groups/<group_id>/available-dates/

    Returns:
        {
            "group_id": "inundationMaps",
            "layers": ["fp_inundation", "fp_discharge", "wrf_discharge"],
            "dates": ["2024-09-01", "2024-09-02", ...],
            "count": 30,
            "first_date": "2024-09-01",
            "last_date": "2024-09-30"
        }
    """
    # Check if group exists
    if group_id not in LAYER_GROUPS:
        return Response(
            {
                'error': f'Unknown layer group: {group_id}',
                'available_groups': list(LAYER_GROUPS.keys())
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # Get all layers in group
    layer_ids = LAYER_GROUPS[group_id]

    # Collect dates from all layers
    all_dates = set()

    for layer_id in layer_ids:
        if layer_id in LAYER_DATA_PATHS:
            data_path = LAYER_DATA_PATHS[layer_id]
            layer_dates = scan_directory_for_dates(data_path)
            all_dates.update(layer_dates)

    # Fallback to sample dates in development
    if not all_dates and os.getenv('DJANGO_ENV') == 'development':
        logger.info(f"Using sample dates for group {group_id}")
        all_dates = set(generate_sample_dates(30))

    # Sort dates
    dates = sorted(list(all_dates))

    # Build response
    response_data = {
        'group_id': group_id,
        'layers': layer_ids,
        'dates': dates,
        'count': len(dates),
    }

    if dates:
        response_data['first_date'] = dates[0]
        response_data['last_date'] = dates[-1]

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_date_availability(request, layer_id, date):
    """
    Check if a specific date has data for a layer

    GET /api/layers/<layer_id>/check-date/<date>/

    Returns:
        {
            "layer_id": "fp_inundation",
            "date": "2024-09-15",
            "available": true
        }
    """
    # Validate layer
    if layer_id not in LAYER_DATA_PATHS:
        return Response(
            {'error': f'Unknown layer: {layer_id}'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate date format
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return Response(
            {'error': f'Invalid date format: {date}. Use YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get available dates
    data_path = LAYER_DATA_PATHS[layer_id]
    dates = scan_directory_for_dates(data_path)

    # Check if date is available
    available = date in dates

    return Response(
        {
            'layer_id': layer_id,
            'date': date,
            'available': available
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_layers_dates(request):
    """
    Get available dates for all layers

    GET /api/layers/all-dates/

    Returns:
        {
            "layers": {
                "fp_inundation": {
                    "dates": [...],
                    "count": 30
                },
                ...
            }
        }
    """
    result = {}

    for layer_id, data_path in LAYER_DATA_PATHS.items():
        dates = scan_directory_for_dates(data_path)

        # Fallback to sample dates in development
        if not dates and os.getenv('DJANGO_ENV') == 'development':
            dates = generate_sample_dates(30)

        result[layer_id] = {
            'dates': dates,
            'count': len(dates),
            'first_date': dates[0] if dates else None,
            'last_date': dates[-1] if dates else None,
        }

    return Response({'layers': result}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_latest_date(request, layer_id):
    """
    Get the latest available date for a specific layer

    GET /api/layers/<layer_id>/latest-date/

    Returns:
        {
            "layer_id": "Alerts",
            "latest_date": "2025-10-04",
            "formatted_date": "20251004",
            "year": "2025",
            "month": "10",
            "day": "04"
        }
    """
    # Check if layer exists
    if layer_id not in LAYER_DATA_PATHS:
        return Response(
            {
                'error': f'Unknown layer: {layer_id}',
                'available_layers': list(LAYER_DATA_PATHS.keys())
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # Get data path for layer
    data_path = LAYER_DATA_PATHS[layer_id]

    # Scan directory for dates
    dates = scan_directory_for_dates(data_path)

    # Fallback to sample dates in development
    if not dates and os.getenv('DJANGO_ENV') == 'development':
        logger.info(f"Using sample dates for layer {layer_id}")
        dates = generate_sample_dates(30)

    if not dates:
        return Response(
            {
                'layer_id': layer_id,
                'latest_date': None,
                'error': 'No dates available for this layer'
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # Get latest date
    latest_date = dates[-1]
    date_obj = datetime.strptime(latest_date, '%Y-%m-%d')

    # Build response with different date formats
    response_data = {
        'layer_id': layer_id,
        'latest_date': latest_date,
        'formatted_date': date_obj.strftime('%Y%m%d'),
        'year': date_obj.strftime('%Y'),
        'month': date_obj.strftime('%m'),
        'day': date_obj.strftime('%d'),
    }

    return Response(response_data, status=status.HTTP_200_OK)
