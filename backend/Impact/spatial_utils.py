"""
Spatial filtering utilities for GeoJSON data
"""
from django.contrib.gis.geos import Point
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


def filter_geojson_by_country(geojson_data, country_name):
    """
    Filter GeoJSON point features by country using PostGIS spatial query
    
    Args:
        geojson_data: GeoJSON FeatureCollection with Point features
        country_name: Name of the country to filter by
    
    Returns:
        Filtered GeoJSON FeatureCollection
    """
    from Impact.models import Admin1
    
    if not geojson_data or not geojson_data.get('features'):
        return geojson_data
    
    try:
        # Get the country boundary from Admin1 (uses PostGIS index for fast lookup)
        country_geom = Admin1.objects.filter(
            Q(country__iexact=country_name) | Q(land_under__iexact=country_name)
        ).first()
        
        if not country_geom:
            logger.warning(f"Country '{country_name}' not found in Admin1 boundaries")
            # Country not found, return empty result
            return {
                **geojson_data,
                'features': []
            }
        
        # Filter points using PostGIS spatial intersection
        filtered_features = []
        for feature in geojson_data['features']:
            if feature.get('geometry', {}).get('type') == 'Point':
                coords = feature['geometry']['coordinates']
                point = Point(coords[0], coords[1])  # lon, lat
                
                # Use PostGIS intersects for fast spatial check
                if country_geom.geom.intersects(point):
                    filtered_features.append(feature)
        
        logger.info(f"Filtered {len(geojson_data['features'])} -> {len(filtered_features)} points for {country_name}")
        
        return {
            **geojson_data,
            'features': filtered_features
        }
    
    except Exception as e:
        logger.error(f"Error filtering by country {country_name}: {e}")
        return geojson_data  # Return unfiltered on error
