from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from drf_spectacular.openapi import AutoSchema
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.http import JsonResponse, Http404
from django.conf import settings
import os
import json
from datetime import datetime
from .serializers import (
    WaterBodiesSerializer,
    Admin0Serializer, Admin0ListSerializer,
    Admin1Serializer, Admin1ListSerializer, Admin2Serializer, Admin2ListSerializer,
    MonitoringStationSerializer, MergedDeterministicGeoJSONSerializer,
    MergedDeterministicGeoJSONMetadataSerializer, HydroRiversSerializer,
    EnsembleControlPointSerializer,
    EnsembleControlPointListSerializer
)
from Impact.models import (
    WaterBodies,
    MergedDeterministicGeoJSON, GeoSFMForecastGeoJSON, Admin0, Admin1, Admin2, MonitoringStation,
    HydroRivers, EnsembleControlPoint
)
from Impact.spatial_utils import filter_geojson_by_country

# Removed old impact layer ViewSets (Affected/Displaced/Impacted models)

@extend_schema(tags=['waterbodies'])
class WaterbodiesViewSet(viewsets.ReadOnlyModelViewSet):
    """API for Water Bodies - returns GeoJSON with pagination"""
    schema = AutoSchema()
    queryset = WaterBodies.objects.all()
    serializer_class = WaterBodiesSerializer
    # Pagination enabled by default (using REST_FRAMEWORK PAGE_SIZE from settings)


# ============ NEW APIS FOR MODELS WITH DATA ============

@extend_schema(tags=['admin-boundaries'])
class Admin0ViewSet(viewsets.ReadOnlyModelViewSet):
    """API for Admin Level 0 (Country) boundaries - returns GeoJSON with pagination"""
    schema = AutoSchema()
    queryset = Admin0.objects.all()

    def get_serializer_class(self):
        """Use lightweight serializer for list views, except for geojson action"""
        if self.action == 'geojson':
            return Admin0Serializer
        if self.action == 'list':
            return Admin0ListSerializer
        return Admin0Serializer

    @action(detail=False, methods=['get'])
    def geojson(self, request):
        """Return all Admin0 boundaries as GeoJSON FeatureCollection (no pagination)"""
        queryset = self.get_queryset()
        serializer = Admin0Serializer(queryset, many=True)

        # Convert to FeatureCollection format
        features = []
        for item in serializer.data.get('features', serializer.data):
            if isinstance(item, dict):
                features.append(item)

        return Response({
            'type': 'FeatureCollection',
            'features': features
        })
    # Pagination enabled by default (using REST_FRAMEWORK PAGE_SIZE from settings)


@extend_schema(tags=['admin-boundaries'])
class Admin1ViewSet(viewsets.ReadOnlyModelViewSet):
    """API for Admin Level 1 boundaries - returns GeoJSON with pagination"""
    schema = AutoSchema()
    queryset = Admin1.objects.all()

    def get_serializer_class(self):
        """Use lightweight serializer for list views"""
        if self.action == 'list':
            return Admin1ListSerializer
        return Admin1Serializer
    # Pagination enabled by default (using REST_FRAMEWORK PAGE_SIZE from settings)


@extend_schema(tags=['admin-boundaries'])
class Admin2ViewSet(viewsets.ReadOnlyModelViewSet):
    """API for Admin Level 2 boundaries - returns GeoJSON with pagination"""
    schema = AutoSchema()
    queryset = Admin2.objects.all()

    def get_serializer_class(self):
        """Use lightweight serializer for list views"""
        if self.action == 'list':
            return Admin2ListSerializer
        return Admin2Serializer
    # Pagination enabled by default (using REST_FRAMEWORK PAGE_SIZE from settings)


@extend_schema(tags=['monitoring-stations'])
class MonitoringStationViewSet(viewsets.ReadOnlyModelViewSet):
    """API for Monitoring Stations"""
    schema = AutoSchema()
    queryset = MonitoringStation.objects.all()
    serializer_class = MonitoringStationSerializer


@extend_schema(tags=['rivers'])
class HydroRiversViewSet(viewsets.ReadOnlyModelViewSet):
    """API for HydroRIVERS River Network Data"""
    schema = AutoSchema()
    queryset = HydroRivers.objects.all()
    serializer_class = HydroRiversSerializer


# Removed IBEW v2 ViewSets

@extend_schema(
    tags=['geojson'],
    parameters=[
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Date in YYYY-MM-DD format',
            required=True
        )
    ],
    responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.STR}
)
@api_view(['GET'])
def get_geojson_by_date(request, date):
    """
    Serve GeoJSON data for a specific date from merged_geojson_output directory
    """
    try:
        # Parse and validate date
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        year = date_obj.strftime('%Y')
        month = date_obj.strftime('%m')
        filename = f'merged_data_{date_obj.strftime("%Y%m%d")}.geojson'
        
        # Construct file path - merged_geojson_output is one level up from backend
        base_dir = os.path.dirname(settings.BASE_DIR)
        file_path = os.path.join(base_dir, 'merged_geojson_output', year, month, filename)
        
        # Initialize fallback variables
        latest_file = None
        latest_date = None
        fallback_used = False
        
        # Check if file exists
        if not os.path.exists(file_path):
            # Try to find the latest available file if exact date doesn't exist
            base_dir = os.path.dirname(settings.BASE_DIR)
            merged_dir = os.path.join(base_dir, 'merged_geojson_output')
            
            if os.path.exists(merged_dir):
                for root, dirs, files in os.walk(merged_dir):
                    for filename in files:
                        if filename.startswith('merged_data_') and filename.endswith('.geojson'):
                            date_str = filename.replace('merged_data_', '').replace('.geojson', '')
                            if len(date_str) == 8 and date_str.isdigit():
                                file_date = datetime.strptime(date_str, '%Y%m%d')
                                if latest_date is None or file_date > latest_date:
                                    latest_date = file_date
                                    latest_file = os.path.join(root, filename)
            
            if latest_file and latest_date:
                # Use the latest available file instead
                file_path = latest_file
                fallback_used = True
                print(f"Data for {date} not found, using latest available: {latest_date.strftime('%Y-%m-%d')}")
            else:
                raise Http404(f'GeoJSON data not found for date {date} and no fallback data available')
        
        # Read and return GeoJSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        # Add metadata about the actual date being served if fallback was used
        if fallback_used and latest_date:
            actual_date_served = latest_date.strftime('%Y-%m-%d')
            response = JsonResponse(geojson_data, safe=False)
            response['X-Actual-Date'] = actual_date_served
            response['X-Fallback-Used'] = 'true'
            return response
        
        return JsonResponse(geojson_data, safe=False)
    
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@extend_schema(
    tags=['geojson'],
    parameters=[
        OpenApiParameter(
            name='requested_date',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Requested date in YYYY-MM-DD format',
            required=False
        )
    ],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
def get_best_available_date(request):
    """
    Get the best available date for a requested date.
    Returns the requested date if available, otherwise the latest available date.
    """
    try:
        requested_date = request.GET.get('requested_date')
        base_dir = os.path.dirname(settings.BASE_DIR)
        merged_dir = os.path.join(base_dir, 'merged_geojson_output')
        
        # Get all available dates
        available_dates = []
        if os.path.exists(merged_dir):
            for root, dirs, files in os.walk(merged_dir):
                for filename in files:
                    if filename.startswith('merged_data_') and filename.endswith('.geojson'):
                        date_str = filename.replace('merged_data_', '').replace('.geojson', '')
                        if len(date_str) == 8 and date_str.isdigit():
                            formatted_date = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
                            available_dates.append(formatted_date)
        
        available_dates.sort(reverse=True)  # Most recent first
        
        if not available_dates:
            return JsonResponse({
                'error': 'No data available',
                'available_dates': []
            }, status=404)
        
        # Determine best date
        best_date = available_dates[0]  # Default to latest
        is_fallback = False
        fallback_reason = None
        
        if requested_date:
            if requested_date in available_dates:
                best_date = requested_date
            else:
                is_fallback = True
                # Check if it's today
                today = datetime.now().strftime('%Y-%m-%d')
                if requested_date == today:
                    fallback_reason = 'today_not_available'
                else:
                    fallback_reason = 'date_not_available'
        
        return JsonResponse({
            'requested_date': requested_date,
            'best_date': best_date,
            'is_fallback': is_fallback,
            'fallback_reason': fallback_reason,
            'latest_available': available_dates[0] if available_dates else None,
            'total_dates': len(available_dates)
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@extend_schema(
    tags=['geojson'],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
def get_available_dates(request):
    """
    Get list of available dates for GeoJSON data
    """
    try:
        base_dir = os.path.dirname(settings.BASE_DIR)
        merged_dir = os.path.join(base_dir, 'merged_geojson_output')
        
        available_dates = []
        
        if os.path.exists(merged_dir):
            for year in os.listdir(merged_dir):
                year_path = os.path.join(merged_dir, year)
                if os.path.isdir(year_path) and year.isdigit():
                    for month in os.listdir(year_path):
                        month_path = os.path.join(year_path, month)
                        if os.path.isdir(month_path) and month.isdigit():
                            for filename in os.listdir(month_path):
                                if filename.startswith('merged_data_') and filename.endswith('.geojson'):
                                    # Extract date from filename
                                    date_str = filename.replace('merged_data_', '').replace('.geojson', '')
                                    if len(date_str) == 8 and date_str.isdigit():
                                        formatted_date = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
                                        available_dates.append(formatted_date)
        
        available_dates.sort(reverse=True)
        return JsonResponse({'dates': available_dates})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============ MERGED DETERMINISTIC GEOJSON API VIEWS ============

@extend_schema(tags=['deterministic-forecast'])
class MergedDeterministicGeoJSONViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for merged deterministic forecast GeoJSON data"""
    schema = AutoSchema()
    queryset = MergedDeterministicGeoJSON.objects.all().order_by('-data_date')
    serializer_class = MergedDeterministicGeoJSONSerializer
    
    @action(detail=False, methods=['get'], url_path='dates')
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True)
        return Response({
            'dates': [date.strftime('%Y-%m-%d') for date in dates],
            'count': len(dates)
        })
    
    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """Get the latest available GeoJSON data"""
        latest_record = self.queryset.first()
        if not latest_record:
            return Response({'error': 'No data available'}, status=404)
        
        serializer = self.get_serializer(latest_record)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-date/(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})')
    def by_date(self, request, date=None):
        """Get GeoJSON data by specific date (YYYY-MM-DD)"""
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            record = self.queryset.filter(data_date=date_obj).first()
            
            if not record:
                # Try to find closest date
                latest = self.queryset.first()
                if latest:
                    serializer = self.get_serializer(latest)
                    response = Response(serializer.data)
                    response['X-Actual-Date'] = latest.data_date.strftime('%Y-%m-%d')
                    response['X-Fallback-Used'] = 'true'
                    return response
                else:
                    return Response({'error': f'No data available for {date}'}, status=404)
            
            serializer = self.get_serializer(record)
            return Response(serializer.data)
            
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)


@extend_schema(
    tags=['deterministic-forecast'],
    parameters=[
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Date in YYYY-MM-DD format',
            required=True
        )
    ],
    responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.STR}
)
@api_view(['GET'])
def get_deterministic_geojson_by_date(request, date):
    """
    Get merged deterministic GeoJSON data for a specific date from database
    Returns only the GeoJSON content - optimized with database-only query (no full load)
    """
    from django.core.cache import cache

    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()

        # Check cache first (1 hour cache)
        cache_key = f'deterministic_geojson_{date}'
        cached_response = cache.get(cache_key)
        if cached_response:
            response = JsonResponse(cached_response['data'], safe=False)
            for header, value in cached_response['headers'].items():
                response[header] = value
            response['X-Cache-Hit'] = 'true'
            return response

        # Use only() to fetch only required fields
        record = MergedDeterministicGeoJSON.objects.filter(
            data_date=date_obj
        ).only('geojson_data', 'data_date', 'feature_count').first()

        if not record:
            # Fallback to latest available
            latest = MergedDeterministicGeoJSON.objects.only(
                'geojson_data', 'data_date', 'feature_count'
            ).order_by('-data_date').first()

            if latest:
                headers = {
                    'X-Actual-Date': latest.data_date.strftime('%Y-%m-%d'),
                    'X-Fallback-Used': 'true',
                    'X-Feature-Count': str(latest.feature_count),
                    'X-Cache-Hit': 'false',
                }
                # Cache for 1 hour
                cache.set(cache_key, {'data': latest.geojson_data, 'headers': headers}, 3600)

                response = JsonResponse(latest.geojson_data, safe=False)
                for header, value in headers.items():
                    response[header] = value
                return response
            else:
                return JsonResponse({'error': f'No data available for {date}'}, status=404)

        # Cache and return the GeoJSON content
        headers = {
            'X-Data-Date': record.data_date.strftime('%Y-%m-%d'),
            'X-Feature-Count': str(record.feature_count),
            'X-Cache-Hit': 'false',
        }
        cache.set(cache_key, {'data': record.geojson_data, 'headers': headers}, 3600)

        response = JsonResponse(record.geojson_data, safe=False)
        for header, value in headers.items():
            response[header] = value
        return response

    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@extend_schema(
    tags=['deterministic-forecast'],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
def get_deterministic_available_dates(request):
    """
    Get list of available dates for deterministic forecast data from database
    """
    try:
        dates_qs = MergedDeterministicGeoJSON.objects.values(
            'data_date', 'feature_count', 'created_at'
        ).order_by('-data_date')
        
        dates_list = []
        for item in dates_qs:
            dates_list.append({
                'date': item['data_date'].strftime('%Y-%m-%d'),
                'features': item['feature_count'],
                'created': item['created_at']
            })
        
        return JsonResponse({
            'dates': [item['date'] for item in dates_list],
            'detailed_dates': dates_list,
            'count': len(dates_list),
            'latest': dates_list[0]['date'] if dates_list else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@extend_schema(
    tags=['deterministic-forecast'],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
def get_deterministic_latest(request):
    """
    Get the latest available deterministic forecast GeoJSON data
    """
    try:
        latest = MergedDeterministicGeoJSON.objects.order_by('-data_date').first()
        
        if not latest:
            return JsonResponse({'error': 'No data available'}, status=404)
        
        # Return just the GeoJSON content
        response = JsonResponse(latest.geojson_data, safe=False)
        response['X-Data-Date'] = latest.data_date.strftime('%Y-%m-%d')
        response['X-Feature-Count'] = latest.feature_count
        response['X-Is-Latest'] = 'true'
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============ GEOSFM FORECAST ENDPOINTS ============

@extend_schema(
    tags=['geosfm-forecast'],
    parameters=[
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Date in YYYY-MM-DD format',
            required=True
        )
    ],
    responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.STR}
)
@api_view(['GET'])
def get_geosfm_geojson_by_date(request, date):
    """
    Get GeoSFM forecast GeoJSON data for a specific date from database
    Returns only the GeoJSON content for faster loading
    """
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        record = GeoSFMForecastGeoJSON.objects.filter(data_date=date_obj).first()

        if not record:
            # Fallback to latest available
            latest = GeoSFMForecastGeoJSON.objects.order_by('-data_date').first()
            if latest:
                response = JsonResponse(latest.geojson_data, safe=False)
                response['X-Actual-Date'] = latest.data_date.strftime('%Y-%m-%d')
                response['X-Fallback-Used'] = 'true'
                response['X-Feature-Count'] = latest.feature_count
                response['X-Matched-Count'] = latest.matched_count
                return response
            else:
                return JsonResponse({'error': f'No GeoSFM data available for {date}'}, status=404)

        # Return just the GeoJSON content
        response = JsonResponse(record.geojson_data, safe=False)
        response['X-Data-Date'] = record.data_date.strftime('%Y-%m-%d')
        response['X-Feature-Count'] = record.feature_count
        response['X-Matched-Count'] = record.matched_count
        return response

    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        # Return 404 if table doesn't exist or query fails (don't throw 500)
        return JsonResponse({'error': 'No GeoSFM data available'}, status=404)


@extend_schema(
    tags=['geosfm-forecast'],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
def get_geosfm_available_dates(request):
    """
    Get list of available dates for GeoSFM forecast data from database
    """
    try:
        dates_qs = GeoSFMForecastGeoJSON.objects.values(
            'data_date', 'feature_count', 'matched_count', 'created_at'
        ).order_by('-data_date')

        dates_list = []
        for item in dates_qs:
            dates_list.append({
                'date': item['data_date'].strftime('%Y-%m-%d'),
                'features': item['feature_count'],
                'matched': item['matched_count'],
                'created': item['created_at']
            })

        return JsonResponse({
            'dates': [item['date'] for item in dates_list],
            'detailed_dates': dates_list,
            'count': len(dates_list),
            'latest': dates_list[0]['date'] if dates_list else None
        })

    except Exception as e:
        # Return empty list if table doesn't exist or query fails (don't throw 500)
        return JsonResponse({
            'dates': [],
            'detailed_dates': [],
            'count': 0,
            'latest': None
        })


@extend_schema(
    tags=['geosfm-forecast'],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
def get_geosfm_latest(request):
    """
    Get the latest available GeoSFM forecast GeoJSON data
    """
    try:
        latest = GeoSFMForecastGeoJSON.objects.order_by('-data_date').first()

        if not latest:
            return JsonResponse({'error': 'No GeoSFM data available'}, status=404)

        # Return just the GeoJSON content
        response = JsonResponse(latest.geojson_data, safe=False)
        response['X-Data-Date'] = latest.data_date.strftime('%Y-%m-%d')
        response['X-Feature-Count'] = latest.feature_count
        response['X-Matched-Count'] = latest.matched_count
        response['X-Is-Latest'] = 'true'
        return response

    except Exception as e:
        # Return 404 if table doesn't exist or query fails (don't throw 500)
        return JsonResponse({'error': 'No GeoSFM data available'}, status=404)


@extend_schema(
    tags=['admin-boundaries'],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
def get_admin_boundaries(request):
    """
    Get admin boundaries as GeoJSON data - simple working approach like monitoring stations
    """
    try:
        from django.contrib.gis.serializers import geojson
        
        # Get all admin boundaries
        admin_data = Admin1.objects.all()
        
        # Create GeoJSON manually for reliable results
        features = []
        for admin in admin_data:
            feature = {
                "type": "Feature",
                "geometry": json.loads(admin.geom.geojson),
                "properties": {
                    "objectid": admin.objectid,
                    "country": admin.country,
                    "land_under": admin.land_under,
                    "shape_area": admin.shape_area,
                    "shape_leng": admin.shape_leng
                }
            }
            features.append(feature)
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        response = JsonResponse(geojson_data, safe=False)
        response['X-Feature-Count'] = len(features)
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
def get_merged_forecast_from_file(request, date=None):
    """
    Serve pre-merged GeoJSON files from remote SFTP server or local disk
    WITH CACHING for improved performance
    
    Usage:
    - /api/v1/merged-forecast/2025-10-20/          - Get specific date
    - /api/v1/merged-forecast/2025-10-20/?country=Kenya  - Get filtered by country
    - /api/v1/merged-forecast/dates/               - List available dates
    
    Caching:
    - GeoJSON data: cached for 1 hour per date
    - Dates list: cached for 15 minutes
    """
    from pathlib import Path
    from datetime import datetime
    import paramiko
    from io import BytesIO
    from django.contrib.gis.geos import Point
    from django.core.cache import cache
    
    # SFTP Configuration from environment
    SFTP_HOST = os.environ.get('SFTP_HOST')
    SFTP_PORT = int(os.environ.get('SFTP_PORT', 22))
    SFTP_USERNAME = os.environ.get('SFTP_USERNAME')
    SFTP_PASSWORD = os.environ.get('SFTP_PASSWORD')
    REMOTE_DIR = "/home/floodproofs/merged_forecasts"
    
    # Check if we have SFTP credentials
    use_sftp = all([SFTP_HOST, SFTP_USERNAME, SFTP_PASSWORD])
    
    # List available dates
    if request.path.endswith('/dates/'):
        # Check cache first (15 minute cache)
        cache_key = 'merged_forecast_dates_list'
        cached_dates = cache.get(cache_key)
        
        if cached_dates is not None:
            return JsonResponse(cached_dates)
        
        try:
            dates = []
            
            if use_sftp:
                # Connect to SFTP and list files with timeout
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USERNAME, password=SFTP_PASSWORD, timeout=10)
                sftp = ssh.open_sftp()
                
                try:
                    # Set SFTP channel timeout
                    sftp.get_channel().settimeout(15)
                    files = sftp.listdir(REMOTE_DIR)
                    for filename in sorted(files, reverse=True):
                        if filename.startswith('merged_data_') and filename.endswith('.geojson'):
                            date_str = filename.replace('merged_data_', '').replace('.geojson', '')
                            try:
                                # Parse date and validate it's a real date
                                date_obj = datetime.strptime(date_str, '%Y%m%d')
                                # Ensure the date is valid by converting back and comparing
                                # This catches cases like 2025-11-84 which strptime doesn't reject
                                if date_obj.strftime('%Y%m%d') != date_str:
                                    continue
                                dates.append({
                                    'date': date_obj.strftime('%Y-%m-%d'),
                                    'filename': filename
                                })
                            except (ValueError, OverflowError):
                                continue
                except Exception as sftp_error:
                    # If SFTP fails, fall back to local files
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"SFTP error: {sftp_error}, falling back to local files")
                    use_sftp = False
                finally:
                    try:
                        sftp.close()
                        ssh.close()
                    except:
                        pass
            
            if not use_sftp:
                # Fallback to local filesystem
                MERGED_DIR = Path("/home/floodproofs/merged_forecasts")
                if not MERGED_DIR.exists():
                    MERGED_DIR = Path(settings.BASE_DIR).parent / "merged_forecasts"
                
                if MERGED_DIR.exists():
                    files = sorted(MERGED_DIR.glob("merged_data_*.geojson"), reverse=True)
                    for file in files:
                        date_str = file.stem.replace('merged_data_', '')
                        try:
                            # Parse date and validate it's a real date
                            date_obj = datetime.strptime(date_str, '%Y%m%d')
                            # Ensure the date is valid by converting back and comparing
                            # This catches cases like 2025-11-84 which strptime doesn't reject
                            if date_obj.strftime('%Y%m%d') != date_str:
                                continue
                            dates.append({
                                'date': date_obj.strftime('%Y-%m-%d'),
                                'filename': file.name,
                                'size_mb': round(file.stat().st_size / (1024 * 1024), 2)
                            })
                        except (ValueError, OverflowError):
                            continue
            
            result = {
                'dates': dates,
                'count': len(dates),
                'source': 'sftp' if use_sftp else 'local'
            }
            
            # Cache for 15 minutes (900 seconds)
            cache.set(cache_key, result, 900)
            
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e), 'source': 'sftp' if use_sftp else 'local'}, status=500)
    
    # Get specific date
    if not date:
        return JsonResponse({'error': 'Date parameter required. Use YYYY-MM-DD format'}, status=400)
    
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_str = date_obj.strftime('%Y%m%d')
        filename = f"merged_data_{date_str}.geojson"
        
        # Check if country filter is requested
        country = request.GET.get('country')
        
        # Create cache key (include country filter if present)
        cache_key = f'merged_forecast_{date_str}'
        if country:
            cache_key = f'merged_forecast_{date_str}_{country}'
        
        # Check cache first (1 hour cache = 3600 seconds)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = JsonResponse(cached_data['geojson'], safe=False)
            for header, value in cached_data['headers'].items():
                response[header] = value
            response['X-Cache-Hit'] = 'true'
            return response
        
        if use_sftp:
            # Fetch file from SFTP with timeout
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USERNAME, password=SFTP_PASSWORD, timeout=10)
            sftp = ssh.open_sftp()
            
            try:
                # Set SFTP channel timeout
                sftp.get_channel().settimeout(60)
                remote_path = f"{REMOTE_DIR}/{filename}"
                file_buffer = BytesIO()
                sftp.getfo(remote_path, file_buffer)
                file_buffer.seek(0)
                geojson_data = json.load(file_buffer)
                file_stat = sftp.stat(remote_path)
                
                # Apply country filter if requested
                original_count = len(geojson_data.get('features', []))
                if country:
                    geojson_data = filter_geojson_by_country(geojson_data, country)
                
                # Prepare headers
                headers = {
                    'X-Forecast-Date': date_obj.strftime('%Y-%m-%d'),
                    'X-Feature-Count': len(geojson_data.get('features', [])),
                    'X-Original-Count': original_count,
                    'X-File-Size-MB': round(file_stat.st_size / (1024 * 1024), 2),
                    'X-Source': 'sftp',
                    'X-Cache-Hit': 'false'
                }
                if country:
                    headers['X-Country-Filter'] = country
                
                # Cache the result for 1 hour (3600 seconds)
                cache.set(cache_key, {
                    'geojson': geojson_data,
                    'headers': headers
                }, 3600)
                
                response = JsonResponse(geojson_data, safe=False)
                for header, value in headers.items():
                    response[header] = value
                return response
            except FileNotFoundError:
                return JsonResponse({
                    'error': f'No data found for {date}',
                    'hint': 'Use /api/v1/merged-forecast/dates/ to see available dates'
                }, status=404)
            finally:
                sftp.close()
                ssh.close()
        else:
            # Fallback to local filesystem
            MERGED_DIR = Path("/home/floodproofs/merged_forecasts")
            if not MERGED_DIR.exists():
                MERGED_DIR = Path(settings.BASE_DIR).parent / "merged_forecasts"
            
            file_path = MERGED_DIR / filename
            if not file_path.exists():
                return JsonResponse({
                    'error': f'No data found for {date}',
                    'hint': 'Use /api/v1/merged-forecast/dates/ to see available dates'
                }, status=404)
            
            with open(file_path, 'r') as f:
                geojson_data = json.load(f)
            
            # Apply country filter if requested
            original_count = len(geojson_data.get('features', []))
            if country:
                geojson_data = filter_geojson_by_country(geojson_data, country)
            
            # Prepare headers
            headers = {
                'X-Forecast-Date': date_obj.strftime('%Y-%m-%d'),
                'X-Feature-Count': len(geojson_data.get('features', [])),
                'X-Original-Count': original_count,
                'X-File-Size-MB': round(file_path.stat().st_size / (1024 * 1024), 2),
                'X-Source': 'local',
                'X-Cache-Hit': 'false'
            }
            if country:
                headers['X-Country-Filter'] = country
            
            # Cache the result for 1 hour (3600 seconds)
            cache.set(cache_key, {
                'geojson': geojson_data,
                'headers': headers
            }, 3600)
            
            response = JsonResponse(geojson_data, safe=False)
            for header, value in headers.items():
                response[header] = value
            return response
        
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
def get_map_layer_config(request):
    """
    Get enabled map layers from admin config
    Simple endpoint - no caching complexity
    """
    try:
        layers = MapLayerConfig.objects.filter(enabled=True)
        
        layer_data = [{
            'id': layer.id,
            'name': layer.name,
            'technical_name': layer.technical_name,
            'category': layer.category,
            'url': layer.external_url,
            'layer_names': [name.strip() for name in layer.layer_names.split(',') if name.strip()],
            'default_visible': layer.default_visible,
            'display_order': layer.display_order
        } for layer in layers]
        
        return JsonResponse({'layers': layer_data, 'count': len(layer_data)})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
def get_merged_forecast_from_db(request, date=None):
    """
    Serve pre-merged GeoJSON files from DATABASE
    This replaces SFTP/file-based loading with database-backed storage

    Usage:
    - /api/v1/merged-forecast-db/2025-10-20/          - Get specific date
    - /api/v1/merged-forecast-db/2025-10-20/?country=Kenya  - Get filtered by country
    - /api/v1/merged-forecast-db/dates/               - List available dates

    Caching:
    - GeoJSON data: cached for 1 hour per date
    - Dates list: cached for 15 minutes
    """
    from datetime import datetime
    from django.core.cache import cache

    # List available dates
    if request.path.endswith('/dates/'):
        # Check cache first (15 minute cache)
        cache_key = 'merged_forecast_db_dates_list'
        cached_dates = cache.get(cache_key)

        if cached_dates is not None:
            return JsonResponse(cached_dates)

        try:
            # Query database for available dates
            forecasts = MergedDeterministicGeoJSON.objects.all().order_by('-data_date')

            dates = []
            for forecast in forecasts:
                dates.append({
                    'date': forecast.data_date.strftime('%Y-%m-%d'),
                    'filename': forecast.file_path or f"merged_data_{forecast.date_string}.geojson",
                    'feature_count': forecast.feature_count,
                    'file_count': forecast.file_count,
                })

            result = {
                'dates': dates,
                'count': len(dates),
                'source': 'database'
            }

            # Cache for 15 minutes (900 seconds)
            cache.set(cache_key, result, 900)

            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e), 'source': 'database'}, status=500)

    # Get specific date
    if not date:
        return JsonResponse({'error': 'Date parameter required. Use YYYY-MM-DD format'}, status=400)

    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')

        # Check if country filter is requested
        country = request.GET.get('country')

        # Create cache key (include country filter if present)
        cache_key = f'merged_forecast_db_{date}'
        if country:
            cache_key = f'merged_forecast_db_{date}_{country}'

        # Check cache first (1 hour cache = 3600 seconds)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = JsonResponse(cached_data['geojson'], safe=False)
            for header, value in cached_data['headers'].items():
                response[header] = value
            response['X-Cache-Hit'] = 'true'
            return response

        # Query database
        try:
            forecast = MergedDeterministicGeoJSON.objects.get(data_date=date_obj.date())
        except MergedDeterministicGeoJSON.DoesNotExist:
            # Fallback to latest available date
            latest_forecast = MergedDeterministicGeoJSON.objects.order_by('-data_date').first()
            if latest_forecast:
                forecast = latest_forecast
                logger.warning(f'No data for {date}, falling back to latest: {latest_forecast.data_date}')
            else:
                return JsonResponse({
                    'error': f'No data found for {date}',
                    'hint': 'Use /api/v1/merged-forecast-db/dates/ to see available dates',
                    'source': 'database'
                }, status=404)

        # Get GeoJSON data
        geojson_data = forecast.geojson_data

        # Apply country filter if requested
        original_count = len(geojson_data.get('features', []))
        if country:
            geojson_data = filter_geojson_by_country(geojson_data, country)

        # Prepare headers
        headers = {
            'X-Forecast-Date': forecast.data_date.strftime('%Y-%m-%d'),
            'X-Feature-Count': len(geojson_data.get('features', [])),
            'X-Original-Count': original_count,
            'X-Source': 'database',
            'X-Cache-Hit': 'false',
            'X-DB-Updated': forecast.updated_at.isoformat() if forecast.updated_at else None,
        }
        if country:
            headers['X-Country-Filter'] = country

        # Cache the result for 1 hour (3600 seconds)
        cache.set(cache_key, {
            'geojson': geojson_data,
            'headers': headers
        }, 3600)

        response = JsonResponse(geojson_data, safe=False)
        for header, value in headers.items():
            if value is not None:
                response[header] = str(value)
        return response

    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e), 'source': 'database'}, status=500)


@extend_schema(tags=['ensemble-control-points'])
class EnsembleControlPointViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for ensemble control points used in forecast merging.

    These control points serve as reference locations for:
    - Merging ensemble forecast data with CSV datasets
    - Spatial matching using GRIDCODE
    - Zone-based filtering

    Query parameters:
    - zone: Filter by zone number (e.g., ?zone=6)
    - gridcode: Filter by gridcode (e.g., ?gridcode=42)
    - admin_name: Filter by admin name (e.g., ?admin_name=Egypt)

    Returns GeoJSON FeatureCollection format.
    """
    schema = AutoSchema()

    def get_serializer_class(self):
        """Use lightweight serializer for list views"""
        if self.action == 'list':
            return EnsembleControlPointListSerializer
        return EnsembleControlPointSerializer

    def get_queryset(self):
        """Optimized queryset with optional filtering"""
        queryset = EnsembleControlPoint.objects.all()

        # Filter by zone
        zone = self.request.query_params.get('zone', None)
        if zone is not None:
            queryset = queryset.filter(zone=zone)

        # Filter by gridcode
        gridcode = self.request.query_params.get('gridcode', None)
        if gridcode is not None:
            queryset = queryset.filter(gridcode=gridcode)

        # Filter by admin_name
        admin_name = self.request.query_params.get('admin_name', None)
        if admin_name is not None:
            queryset = queryset.filter(admin_name__icontains=admin_name)

        return queryset

    @extend_schema(
        summary="Get ensemble control point by GRIDCODE",
        parameters=[
            OpenApiParameter(
                name='gridcode',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='GRIDCODE to filter by'
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_gridcode(self, request):
        """Get control points by GRIDCODE"""
        gridcode = request.query_params.get('gridcode')
        if not gridcode:
            return Response({'error': 'gridcode parameter is required'}, status=400)

        points = EnsembleControlPoint.objects.filter(gridcode=gridcode)
        serializer = EnsembleControlPointSerializer(points, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get ensemble control points by zone",
        parameters=[
            OpenApiParameter(
                name='zone',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Zone number to filter by'
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_zone(self, request):
        """Get control points by zone"""
        zone = request.query_params.get('zone')
        if not zone:
            return Response({'error': 'zone parameter is required'}, status=400)

        points = EnsembleControlPoint.objects.filter(zone=zone)
        serializer = EnsembleControlPointSerializer(points, many=True)
        return Response(serializer.data)
