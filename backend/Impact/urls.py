from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AffectedPopulationViewSet,
    ImpactedGDPViewSet,
    AffectedCropsViewSet,
    AffectedRoadsViewSet,
    DisplacedPopulationViewSet,
    AffectedLivestockViewSet,
    AffectedGrazingLandViewSet,
    SectorDataViewSet,
    SectorForecastViewSet,
)

# Create a router and register viewsets
router = DefaultRouter()

# Registering various ViewSets to the router. Each ViewSet will correspond to a model and handle the related API endpoints.
# The first argument is the URL prefix (e.g., 'affectedPop'), which becomes part of the URL when accessed.
# The second argument is the ViewSet class that handles requests for the corresponding model.
# The `basename` is used to name the URL pattern for the viewset.

# Registering the ViewSet for affected population
router.register(r'affectedPop', AffectedPopulationViewSet, basename='affectedPop')
# Registering the ViewSet for impacted GDP
router.register(r'affectedGDP', ImpactedGDPViewSet, basename='affectedGDP')
# Registering the ViewSet for affected crops
router.register(r'affectedCrops', AffectedCropsViewSet, basename='affectedCrops')
# Registering the ViewSet for affected roads
router.register(r'affectedRoads', AffectedRoadsViewSet, basename='affectedRoads')
# Registering the ViewSet for displaced population
router.register(r'displacedPop', DisplacedPopulationViewSet, basename='displacedPop')
# Registering the ViewSet for affected livestock
router.register(r'affectedLivestock', AffectedLivestockViewSet, basename='affectedLivestock')
# Registering the ViewSet for affected grazing land
router.register(r'affectedGrazingLand', AffectedGrazingLandViewSet, basename='affectedGrazingLand')

#  Registering the ViewSet for sector data
router.register(r'sectorData', SectorDataViewSet, basename='sectorData')
router.register(r'SectorForecast', SectorForecastViewSet, basename='SectorForecast')


# URL patterns list for the Impact app. All URLs for the app will be handled by the viewsets registered above.
urlpatterns = [
    # The `router.urls` includes all the registered routes and automatically maps them to the corresponding viewset actions.
    # This means that for each registered ViewSet, Django will generate the appropriate URL patterns for CRUD operations (GET, POST, PUT, DELETE).
    # The '' (empty string) as the URL pattern means that all the API routes for this app will be prefixed with `/api/` in the main URL configuration.
    path('', include(router.urls)),  # This includes all the registered router URLs
]