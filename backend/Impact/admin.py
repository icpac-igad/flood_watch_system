from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin
from Impact.models import (
    AffectedGrazingLand, AffectedPopulation, ImpactedGDP, AffectedCrops,
    AffectedLivestock, AffectedRoads, DisplacedPopulation,SectorData,SectorForecast,WaterBodies,RiverSection
)

class BaseImpactAdmin(LeafletGeoAdmin):
    # Leaflet settings
    settings_overrides = {
        'DEFAULT_CENTER': (0.0, 36.0),  # Centered on East Africa
        'DEFAULT_ZOOM': 4,
        'MIN_ZOOM': 3,
        'MAX_ZOOM': 18,
    }

@admin.register(AffectedPopulation)
class AffectedPopulationAdmin(BaseImpactAdmin):
    pass

@admin.register(ImpactedGDP)
class ImpactedGDPAdmin(BaseImpactAdmin):
    pass

@admin.register(AffectedCrops)
class AffectedCropsAdmin(BaseImpactAdmin):
    pass

@admin.register(AffectedGrazingLand)
class AffectedGrazingLandAdmin(BaseImpactAdmin):
    pass

@admin.register(AffectedLivestock)
class AffectedLivestockAdmin(BaseImpactAdmin):
    pass

@admin.register(AffectedRoads)
class AffectedRoadsAdmin(BaseImpactAdmin):
    pass

@admin.register(DisplacedPopulation)
class DisplacedPopulationAdmin(BaseImpactAdmin):
    pass

@admin.register(SectorData)
class SectorDataAdmin(BaseImpactAdmin):
    list_display = ['sec_code','sec_name','lat','lon','geom']
    search_fields = ['sec_code','sec_name','basin','geom']

@admin.register(SectorForecast)
class SectorForecastAdmin(BaseImpactAdmin):
    list_display = ['sector', 'model_type', 'time_point']
    search_fields = ['sector', 'model_type', 'time_point']

@admin.register(WaterBodies)
class WaterBodiesAdmin(BaseImpactAdmin):
    list_display = ['name_of_wa', 'type_of_wa']

@admin.register(RiverSection)
class RiverSectionAdmin(BaseImpactAdmin):
    list_display = ['sec_name', 'basin', 'latitude', 'longitude']
    search_fields = ['sec_name', 'basin']
    list_filter = ['basin']

