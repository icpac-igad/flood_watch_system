from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.cache import cache
from google.cloud import storage
from datetime import timedelta
import os
import json

@api_view(['GET'])
def geosfm_forecast_urls(request):
    """
    Generate signed URLs for GeoSFM forecast files from Google Cloud Storage.
    Frontend will fetch data directly from GCS using these temporary URLs.
    
    Query params:
        - date: YYYY-MM-DD format
    
    Returns:
        - urls: List of signed URLs (valid for 15 minutes)
        - metadata: File info (station IDs, timestamps)
    """
    date_str = request.GET.get('date')
    
    if not date_str:
        return Response({'error': 'Date parameter required (YYYY-MM-DD)'}, status=400)
    
    cache_key = f'geosfm_urls_{date_str}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, headers={'X-Cache-Hit': 'true'})
    
    try:
        # Get GCS credentials from environment
        gcs_project = os.environ.get('GCS_PROJECT_ID')
        gcs_bucket = os.environ.get('GCS_BUCKET_NAME')
        gcs_creds = os.environ.get('GCS_CREDENTIALS_JSON')
        
        if not all([gcs_project, gcs_bucket, gcs_creds]):
            return Response({
                'error': 'GCS credentials not configured',
                'message': 'Please add GCS_PROJECT_ID, GCS_BUCKET_NAME, GCS_CREDENTIALS_JSON secrets'
            }, status=500)
        
        # Initialize GCS client
        client = storage.Client.from_service_account_json(gcs_creds, project=gcs_project)
        bucket = client.bucket(gcs_bucket)
        
        # Convert date format: YYYY-MM-DD → YYYY/MM/DD
        year, month, day = date_str.split('-')
        gcs_prefix = f"geosfm/{year}/{month}/{day}/"
        
        # List GeoSFM forecast files for this date
        blobs = bucket.list_blobs(prefix=gcs_prefix)
        
        signed_urls = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                # Generate signed URL (valid for 15 minutes)
                url = blob.generate_signed_url(
                    version='v4',
                    expiration=timedelta(minutes=15),
                    method='GET'
                )
                
                signed_urls.append({
                    'filename': blob.name.split('/')[-1],
                    'url': url,
                    'size': blob.size,
                    'updated': blob.updated.isoformat() if blob.updated else None
                })
        
        if not signed_urls:
            return Response({
                'date': date_str,
                'urls': [],
                'message': f'No GeoSFM forecast data found for {date_str}'
            })
        
        response_data = {
            'date': date_str,
            'urls': signed_urls,
            'count': len(signed_urls),
            'expires_in': '15 minutes'
        }
        
        # Cache for 10 minutes (URLs valid for 15 min)
        cache.set(cache_key, response_data, 600)
        
        return Response(response_data, headers={'X-Cache-Hit': 'false'})
        
    except Exception as e:
        return Response({
            'error': str(e),
            'message': 'Failed to generate signed URLs for GeoSFM data'
        }, status=500)


@api_view(['GET'])
def geosfm_available_dates(request):
    """
    List available GeoSFM forecast dates from Google Cloud Storage.
    Returns empty list if GCS is not configured (not an error).
    """
    cache_key = 'geosfm_dates'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, headers={'X-Cache-Hit': 'true'})

    try:
        gcs_project = os.environ.get('GCS_PROJECT_ID')
        gcs_bucket = os.environ.get('GCS_BUCKET_NAME')
        gcs_creds = os.environ.get('GCS_CREDENTIALS_JSON')

        # Return empty list if GCS not configured (not an error - just unavailable)
        if not all([gcs_project, gcs_bucket, gcs_creds]):
            response_data = {
                'dates': [],
                'count': 0
            }
            cache.set(cache_key, response_data, 900)  # Cache for 15 minutes
            return Response(response_data)

        client = storage.Client.from_service_account_json(gcs_creds, project=gcs_project)
        bucket = client.bucket(gcs_bucket)

        # List all dates with GeoSFM data
        blobs = bucket.list_blobs(prefix='geosfm/')
        dates = set()

        for blob in blobs:
            # Extract date from path: geosfm/YYYY/MM/DD/file.json
            parts = blob.name.split('/')
            if len(parts) >= 4 and parts[0] == 'geosfm':
                year, month, day = parts[1], parts[2], parts[3]
                dates.add(f"{year}-{month}-{day}")

        dates_list = sorted(list(dates), reverse=True)

        response_data = {
            'dates': dates_list,
            'count': len(dates_list)
        }

        # Cache for 15 minutes
        cache.set(cache_key, response_data, 900)

        return Response(response_data, headers={'X-Cache-Hit': 'false'})

    except Exception as e:
        # Return empty list on error (don't throw 500 - just return no data)
        response_data = {
            'dates': [],
            'count': 0
        }
        return Response(response_data)
