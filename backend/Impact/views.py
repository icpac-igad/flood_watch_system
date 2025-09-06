from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from drf_spectacular.openapi import AutoSchema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    AffectedPopulationSerializer, ImpactedGDPSerializer, AffectedCropsSerializer,
    AffectedRoadsSerializer, DisplacedPopulationSerializer, AffectedLivestockSerializer,
    AffectedGrazingLandSerializer, SectorDataSerializer,SectorForecastSerializer,WaterBodiesSerializer
)
from Impact.models import (
    AffectedPopulation, ImpactedGDP, AffectedCrops, AffectedGrazingLand,
    AffectedLivestock, AffectedRoads, DisplacedPopulation, SectorData,SectorForecast,WaterBodies
)

@extend_schema(tags=['affected-population'])
class AffectedPopulationViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = AffectedPopulation.objects.all()
    serializer_class = AffectedPopulationSerializer

@extend_schema(tags=['impacted-gdp'])
class ImpactedGDPViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = ImpactedGDP.objects.all()
    serializer_class = ImpactedGDPSerializer

@extend_schema(tags=['affected-crops'])
class AffectedCropsViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = AffectedCrops.objects.all()
    serializer_class = AffectedCropsSerializer

@extend_schema(tags=['affected-roads'])
class AffectedRoadsViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = AffectedRoads.objects.all()
    serializer_class = AffectedRoadsSerializer

@extend_schema(tags=['displaced-population'])
class DisplacedPopulationViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = DisplacedPopulation.objects.all()
    serializer_class = DisplacedPopulationSerializer

@extend_schema(tags=['affected-livestock'])
class AffectedLivestockViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = AffectedLivestock.objects.all()
    serializer_class = AffectedLivestockSerializer

@extend_schema(tags=['affected-grazing-land'])
class AffectedGrazingLandViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = AffectedGrazingLand.objects.all()
    serializer_class = AffectedGrazingLandSerializer


@extend_schema(tags=['sector-data'])
class SectorDataViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    queryset = SectorData.objects.all()
    serializer_class = SectorDataSerializer

@extend_schema(tags=['sector-forecast'])
class SectorForecastViewSet(viewsets.ReadOnlyModelViewSet):
    schema = AutoSchema()
    queryset = SectorForecast.objects.all()
    serializer_class = SectorForecastSerializer


@extend_schema(tags=['waterbodies'])
class WaterbodiesViewSet(viewsets.ReadOnlyModelViewSet):
    schema = AutoSchema()
    queryset = WaterBodies.objects.all()
    serializer_class = WaterBodiesSerializer


