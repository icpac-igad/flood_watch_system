from rest_framework_gis.serializers import GeoFeatureModelSerializer 
from rest_framework import viewsets,serializers

from .models import AffectedPopulation, ImpactedGDP, AffectedCrops, AffectedRoads, DisplacedPopulation, AffectedLivestock, AffectedGrazingLand, SectorData,SectorForecast,WaterBodies

class AffectedPopulationSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AffectedPopulation
        geo_field = 'geom'
        fields = '__all__'


class ImpactedGDPSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = ImpactedGDP
        geo_field = 'geom'
        fields = '__all__'  


class AffectedCropsSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AffectedCrops
        geo_field = 'geom'
        fields = '__all__'


class AffectedRoadsSerializer(GeoFeatureModelSerializer):    
    class Meta:
        model = AffectedRoads
        geo_field = 'geom'
        fields = '__all__'

class SectorDataSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = SectorData
        geo_field = 'geom'
        fields = '__all__'


class SectorForecastSerializer(serializers.ModelSerializer):
    sector = SectorDataSerializer(read_only=True)  # Nested serializer for the related SectorData

    class Meta:
        model = SectorForecast
        fields = ['id', 'sector', 'model_type', 'time_point', 'forecast_value']

class DisplacedPopulationSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = DisplacedPopulation
        geo_field = 'geom'
        fields = '__all__'


class AffectedLivestockSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AffectedLivestock
        geo_field = 'geom'
        fields = '__all__'


class AffectedGrazingLandSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AffectedGrazingLand
        geo_field = 'geom'
        fields = '__all__'


class WaterBodiesSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = WaterBodies
        geo_field = 'geom'
        fields = '__all__'

