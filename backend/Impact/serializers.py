from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import viewsets,serializers

from .models import (
    WaterBodies, MergedDeterministicGeoJSON, MonitoringStation,
    Admin0, Admin1, Admin2, HydroRivers, EnsembleControlPoint
)

# Removed old impact layer serializers (Affected/Displaced/Impacted/IBEW models)

class MonitoringStationSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = MonitoringStation
        geo_field = 'geometry'
        fields = '__all__'


class WaterBodiesSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = WaterBodies
        geo_field = 'geom'
        fields = '__all__'


class Admin0Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = Admin0
        geo_field = 'geom'
        fields = '__all__'


class Admin0ListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Admin0 list views - metadata only, no geometry"""
    class Meta:
        model = Admin0
        fields = ['objectid', 'gid_0', 'country', 'shape_area']


class Admin1Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = Admin1
        geo_field = 'geom'
        fields = '__all__'


class Admin1ListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Admin1 list views - metadata only, no geometry"""
    class Meta:
        model = Admin1
        fields = ['objectid', 'country', 'land_under', 'shape_area']


class Admin2Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = Admin2
        geo_field = 'geom'
        fields = '__all__'


class Admin2ListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Admin2 list views - metadata only, no geometry"""
    class Meta:
        model = Admin2
        fields = ['objectid', 'country', 'shape_area']


class HydroRiversSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = HydroRivers
        geo_field = 'geometry'
        fields = '__all__'


class MergedDeterministicGeoJSONSerializer(serializers.ModelSerializer):
    """Serializer for merged deterministic forecast GeoJSON data"""
    
    class Meta:
        model = MergedDeterministicGeoJSON
        fields = '__all__'


class MergedDeterministicGeoJSONMetadataSerializer(serializers.ModelSerializer):
    """Lightweight serializer for metadata only (without GeoJSON content)"""

    class Meta:
        model = MergedDeterministicGeoJSON
        fields = ['data_date', 'date_string', 'feature_count', 'file_count', 'created_at', 'updated_at']


# Ensemble Control Points Serializers

class EnsembleControlPointSerializer(GeoFeatureModelSerializer):
    """Serializer for ensemble control points used in forecast merging.

    Returns GeoJSON format with point geometry and all control point attributes.
    """

    class Meta:
        model = EnsembleControlPoint
        geo_field = 'geom'
        fields = '__all__'


class EnsembleControlPointListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views - excludes geometry for better performance"""

    class Meta:
        model = EnsembleControlPoint
        fields = ['id', 'point_id', 'gridcode', 'admin_name', 'x', 'y', 'zone', 'is_node']

