from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from drf_spectacular.openapi import AutoSchema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    ImpactForecastPopulationSerializer, ImpactForecastGDPSerializer, ImpactForecastCropsSerializer,
    ImpactForecastRoadsSerializer, ImpactForecastDisplacedSerializer, ImpactForecastLivestockSerializer,
    ImpactForecastGrazingSerializer
)
from .models import (
    ImpactForecastPopulation, ImpactForecastGDP, ImpactForecastCrops,
    ImpactForecastRoads, ImpactForecastDisplaced, ImpactForecastLivestock,
    ImpactForecastGrazing
)

# ============ IMPACT FORECAST API VIEWS ============

@extend_schema(tags=['impact-forecast-population'])
class ImpactForecastPopulationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for impact forecast population data with date filtering"""
    schema = AutoSchema()
    queryset = ImpactForecastPopulation.objects.all().order_by('-data_date', '-time_run')
    serializer_class = ImpactForecastPopulationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(data_date=date)
        return queryset

    @action(detail=False, methods=['get'], url_path='dates')
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True).distinct().order_by('-data_date')
        return Response({'dates': [date.strftime('%Y-%m-%d') for date in dates if date]})


@extend_schema(tags=['impact-forecast-gdp'])
class ImpactForecastGDPViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for impact forecast GDP data with date filtering"""
    schema = AutoSchema()
    queryset = ImpactForecastGDP.objects.all().order_by('-data_date', '-time_run')
    serializer_class = ImpactForecastGDPSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(data_date=date)
        return queryset

    @action(detail=False, methods=['get'], url_path='dates')
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True).distinct().order_by('-data_date')
        return Response({'dates': [date.strftime('%Y-%m-%d') for date in dates if date]})


@extend_schema(tags=['impact-forecast-crops'])
class ImpactForecastCropsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for impact forecast crops data with date filtering"""
    schema = AutoSchema()
    queryset = ImpactForecastCrops.objects.all().order_by('-data_date', '-time_run')
    serializer_class = ImpactForecastCropsSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(data_date=date)
        return queryset

    @action(detail=False, methods=['get'], url_path='dates')  
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True).distinct().order_by('-data_date')
        return Response({'dates': [date.strftime('%Y-%m-%d') for date in dates if date]})


@extend_schema(tags=['impact-forecast-roads'])
class ImpactForecastRoadsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for impact forecast roads data with date filtering"""
    schema = AutoSchema()
    queryset = ImpactForecastRoads.objects.all().order_by('-data_date', '-time_run')
    serializer_class = ImpactForecastRoadsSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(data_date=date)
        return queryset

    @action(detail=False, methods=['get'], url_path='dates')
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True).distinct().order_by('-data_date')
        return Response({'dates': [date.strftime('%Y-%m-%d') for date in dates if date]})


@extend_schema(tags=['impact-forecast-displaced'])
class ImpactForecastDisplacedViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for impact forecast displaced population data with date filtering"""
    schema = AutoSchema()
    queryset = ImpactForecastDisplaced.objects.all().order_by('-data_date', '-time_run')
    serializer_class = ImpactForecastDisplacedSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(data_date=date)
        return queryset

    @action(detail=False, methods=['get'], url_path='dates')
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True).distinct().order_by('-data_date')
        return Response({'dates': [date.strftime('%Y-%m-%d') for date in dates if date]})


@extend_schema(tags=['impact-forecast-livestock'])
class ImpactForecastLivestockViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for impact forecast livestock data with date filtering"""
    schema = AutoSchema()
    queryset = ImpactForecastLivestock.objects.all().order_by('-data_date', '-time_run')
    serializer_class = ImpactForecastLivestockSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(data_date=date)
        return queryset

    @action(detail=False, methods=['get'], url_path='dates')
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True).distinct().order_by('-data_date')
        return Response({'dates': [date.strftime('%Y-%m-%d') for date in dates if date]})


@extend_schema(tags=['impact-forecast-grazing'])
class ImpactForecastGrazingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for impact forecast grazing land data with date filtering"""
    schema = AutoSchema()
    queryset = ImpactForecastGrazing.objects.all().order_by('-data_date', '-time_run')
    serializer_class = ImpactForecastGrazingSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(data_date=date)
        return queryset

    @action(detail=False, methods=['get'], url_path='dates')
    def available_dates(self, request):
        """Get list of available dates"""
        dates = self.queryset.values_list('data_date', flat=True).distinct().order_by('-data_date')
        return Response({'dates': [date.strftime('%Y-%m-%d') for date in dates if date]})