from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os
from pathlib import Path
import requests
from datetime import datetime, timedelta
import glob

TITILER_BASE_URL = getattr(settings, 'TITILER_BASE_URL', 'http://titiler:8000')

@api_view(['GET'])
def get_raster_files(request):
    """
    Get available raster files from the data directories
    """
    try:
        files = []

        # Check inundation maps
        inundation_dir = '/app/data/inundation_maps'
        if os.path.exists(inundation_dir):
            pattern = os.path.join(inundation_dir, '**/*.tif')
            for file_path in glob.glob(pattern, recursive=True):
                rel_path = os.path.relpath(file_path, '/app')
                files.append({
                    'path': f'/opt/{rel_path}',
                    'name': os.path.basename(file_path),
                    'type': 'inundation',
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })

        # Check merged alerts
        alerts_dir = '/app/data/merged_alerts'
        if os.path.exists(alerts_dir):
            pattern = os.path.join(alerts_dir, '**/*.tif')
            for file_path in glob.glob(pattern, recursive=True):
                rel_path = os.path.relpath(file_path, '/app')
                files.append({
                    'path': f'/opt/{rel_path}',
                    'name': os.path.basename(file_path),
                    'type': 'merged_alerts',
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })

        # Check mapserver hazards data
        hazards_dir = '/app/mapserver_data/hazards'
        if os.path.exists(hazards_dir):
            pattern = os.path.join(hazards_dir, '**/*.tif')
            for file_path in glob.glob(pattern, recursive=True):
                rel_path = os.path.relpath(file_path, '/app')
                files.append({
                    'path': f'/opt/{rel_path}',
                    'name': os.path.basename(file_path),
                    'type': 'hazards',
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })

        files.sort(key=lambda x: x['modified'], reverse=True)

        return Response({
            'files': files,
            'count': len(files),
            'types': ['inundation', 'merged_alerts', 'hazards']
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_raster_info(request):
    """
    Get raster file information via TiTiler
    """
    file_path = request.GET.get('url')
    if not file_path:
        return Response({'error': 'url parameter required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        response = requests.get(f'{TITILER_BASE_URL}/cog/info', params={'url': file_path})
        response.raise_for_status()
        return Response(response.json())
    except requests.RequestException as e:
        return Response({'error': f'TiTiler request failed: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

@api_view(['GET'])
def get_raster_statistics(request):
    """
    Get raster file statistics via TiTiler
    """
    file_path = request.GET.get('url')
    if not file_path:
        return Response({'error': 'url parameter required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        response = requests.get(f'{TITILER_BASE_URL}/cog/statistics', params={'url': file_path})
        response.raise_for_status()
        return Response(response.json())
    except requests.RequestException as e:
        return Response({'error': f'TiTiler request failed: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

@api_view(['GET'])
def get_latest_inundation(request):
    """
    Get the latest inundation map raster file info
    """
    try:
        data_dir = '/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/flood_watch_system/data/inundation_maps'
        pattern = os.path.join(data_dir, '**/flood_hazard_*.tif')
        files = glob.glob(pattern, recursive=True)

        if not files:
            return Response({'error': 'No inundation files found'}, status=status.HTTP_404_NOT_FOUND)

        latest_file = max(files, key=os.path.getmtime)
        rel_path = os.path.relpath(latest_file, '/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/flood_watch_system')
        file_url = f'/opt/{rel_path}'

        # Get file info from TiTiler
        try:
            response = requests.get(f'{TITILER_BASE_URL}/cog/info', params={'url': file_url})
            response.raise_for_status()
            info = response.json()
        except requests.RequestException:
            info = {}

        return Response({
            'file_path': file_url,
            'local_path': latest_file,
            'name': os.path.basename(latest_file),
            'type': 'inundation',
            'modified': datetime.fromtimestamp(os.path.getmtime(latest_file)).isoformat(),
            'size': os.path.getsize(latest_file),
            'info': info,
            'tile_url': f'{TITILER_BASE_URL}/cog/tiles/{{z}}/{{x}}/{{y}}.png?url={file_url}&rescale=0,1&colormap_name=blues&nodata=0',
            'preview_url': f'{TITILER_BASE_URL}/cog/preview.png?url={file_url}&rescale=0,1&colormap_name=blues&nodata=0'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_latest_alerts(request):
    """
    Get the latest merged alerts raster file info
    """
    try:
        data_dir = '/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/flood_watch_system/data/merged_alerts'
        pattern = os.path.join(data_dir, '**/hmc_alert_daily_*.tif')
        files = glob.glob(pattern, recursive=True)

        if not files:
            return Response({'error': 'No alert files found'}, status=status.HTTP_404_NOT_FOUND)

        latest_file = max(files, key=os.path.getmtime)
        rel_path = os.path.relpath(latest_file, '/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/flood_watch_system')
        file_url = f'/opt/{rel_path}'

        # Get file info from TiTiler
        try:
            response = requests.get(f'{TITILER_BASE_URL}/cog/info', params={'url': file_url})
            response.raise_for_status()
            info = response.json()
        except requests.RequestException:
            info = {}

        return Response({
            'file_path': file_url,
            'local_path': latest_file,
            'name': os.path.basename(latest_file),
            'type': 'merged_alerts',
            'modified': datetime.fromtimestamp(os.path.getmtime(latest_file)).isoformat(),
            'size': os.path.getsize(latest_file),
            'info': info,
            'tile_url': f'{TITILER_BASE_URL}/cog/tiles/{{z}}/{{x}}/{{y}}.png?url={file_url}&rescale=1,4&colormap_name=rdylgn_r&nodata=0',
            'preview_url': f'{TITILER_BASE_URL}/cog/preview.png?url={file_url}&rescale=1,4&colormap_name=rdylgn_r&nodata=0'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_raster_dates(request):
    """
    Get available dates from raster filenames
    """
    try:
        data_dir = '/app/merged'
        pattern = os.path.join(data_dir, '**/*.tif')
        files = glob.glob(pattern, recursive=True)

        dates = set()
        for file_path in files:
            filename = os.path.basename(file_path)
            # Extract date from filename patterns like "flood_hazard_map_floodproofs_IGAD_D1_202505010000.tif"
            if 'flood_hazard_map' in filename:
                parts = filename.split('_')
                for part in parts:
                    if len(part) >= 12 and part.isdigit():
                        try:
                            date_str = part[:8]  # YYYYMMDD
                            date_obj = datetime.strptime(date_str, '%Y%m%d')
                            dates.add(date_obj.strftime('%Y-%m-%d'))
                        except ValueError:
                            continue

        return Response({
            'dates': sorted(list(dates), reverse=True),
            'count': len(dates)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_raster_by_date(request, date):
    """
    Get raster files for a specific date
    """
    try:
        # Parse the date
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_pattern = date_obj.strftime('%Y%m%d')
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        data_dir = '/app/merged'
        pattern = os.path.join(data_dir, f'**/*{date_pattern}*.tif')
        files = glob.glob(pattern, recursive=True)

        if not files:
            return Response({'error': f'No raster files found for date {date}'}, status=status.HTTP_404_NOT_FOUND)

        result_files = []
        for file_path in files:
            rel_path = os.path.relpath(file_path, '/app')
            file_url = f'/opt/{rel_path}'

            result_files.append({
                'file_path': file_url,
                'local_path': file_path,
                'name': os.path.basename(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                'size': os.path.getsize(file_path),
                'tile_url': f'{TITILER_BASE_URL}/cog/tiles/{{z}}/{{x}}/{{y}}.png?url={file_url}&rescale=0,1&colormap_name=blues&nodata=0'
            })

        return Response({
            'date': date,
            'files': result_files,
            'count': len(result_files)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)