
# from django.db import models
from django.contrib.gis.db import models 
from django.db import models as django_models


# Base abstract model for all impact-related models
class BaseImpactModel(models.Model):
    """Abstract base model for flood impact data.
    
    Contains common fields shared across all impact models including
    administrative boundaries, impact metrics, and geometry.
    """
    gid_0 = models.CharField(max_length=80, help_text="Country identifier")
    name_0 = models.CharField(max_length=80, help_text="Country name")
    name_1 = models.CharField(max_length=80, help_text="Admin level 1 name")
    engtype_1 = models.CharField(max_length=80, help_text="Admin level 1 type")
    lack_cc = models.FloatField(help_text="Lack of coping capacity indicator")
    cod = models.CharField(max_length=80, help_text="Country code")
    stock = models.FloatField(help_text="Pre-flood stock/baseline value")
    flood_tot = models.FloatField(help_text="Total flood impact value")
    flood_perc = models.FloatField(help_text="Flood impact percentage")
    geom = models.MultiPolygonField(srid=4326)
    
    def __str__(self):
        return f"{self.name_1} - {self.__class__.__name__}"
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['name_0', 'name_1']),
            models.Index(fields=['cod']),
        ]


# 1. Affected population model
class AffectedPopulation(BaseImpactModel):
    """Model representing population affected by flooding."""
    
    class Meta:
        verbose_name_plural = "Affected Population"

# 2. Impacted GDP model
class ImpactedGDP(BaseImpactModel):
    """Model representing GDP impact from flooding."""
    
    class Meta:
        verbose_name_plural = "Impacted GDP"


# 3. Affected crops model
class AffectedCrops(BaseImpactModel):
    """Model representing agricultural crops affected by flooding."""
    
    class Meta:
        verbose_name_plural = "Affected Crops"


# 4. Affected roads model
class AffectedRoads(BaseImpactModel):
    """Model representing road infrastructure affected by flooding."""
    
    class Meta:
        verbose_name_plural = "Affected Roads"


# 5. Displaced population model
class DisplacedPopulation(BaseImpactModel):
    """Model representing population displaced by flooding."""
    
    class Meta:
        verbose_name_plural = "Displaced Population"


# 6. Affected livestock model
class AffectedLivestock(BaseImpactModel):
    """Model representing livestock affected by flooding."""
    
    class Meta:
        verbose_name_plural = "Affected Livestock"


# 7. Affected grazing land model
class AffectedGrazingLand(BaseImpactModel):
    """Model representing grazing land affected by flooding."""
    
    class Meta:
        verbose_name_plural = "Affected Grazing Land"


# 8. Sector data model
class SectorData(models.Model):
    """Model representing hydrological sectors for monitoring.
    
    Contains sector information including administrative boundaries,
    geographic coordinates, and discharge thresholds.
    """
    sec_code = models.BigIntegerField(help_text="Unique sector code")
    sec_name = models.CharField(max_length=80, help_text="Sector name")
    basin = models.CharField(max_length=80, help_text="River basin name")
    domain = models.CharField(max_length=80, help_text="Domain identifier")
    admin_b_l1 = models.CharField(max_length=80, help_text="Admin boundary level 1")
    admin_b_l2 = models.CharField(max_length=80, null=True, help_text="Admin boundary level 2")
    admin_b_l3 = models.CharField(max_length=80, null=True, help_text="Admin boundary level 3")
    sec_rs = models.CharField(max_length=80, help_text="Sector river system")
    area = models.FloatField(null=False, help_text="Sector area in sq km")
    lat = models.FloatField(null=False, help_text="Latitude")
    lon = models.FloatField(null=False, help_text="Longitude")
    q_thr1 = models.FloatField(null=False, help_text="Discharge threshold level 1")
    q_thr2 = models.FloatField(null=False, help_text="Discharge threshold level 2")
    q_thr3 = models.FloatField(null=False, help_text="Discharge threshold level 3")
    cat = models.FloatField(null=True, help_text="Category")
    geom = models.PointField()
    
    def __str__(self):
        return f"{self.sec_name} ({self.sec_code})"

    class Meta:
        verbose_name_plural = "Sector Data"
        indexes = [
            models.Index(fields=['sec_code']),
            models.Index(fields=['basin']),
        ]


# 9. Sector forecast timeseries model
class SectorForecast(models.Model):
    """Model representing forecast time series data for sectors.
    
    Stores discharge forecast values from different weather models
    (GFS, ICON) for each sector at specific time points.
    """
    sector = models.ForeignKey(SectorData, on_delete=models.CASCADE, related_name='forecasts')
    model_type = models.CharField(max_length=10, choices=[('GFS', 'GFS'), ('ICON', 'ICON')], help_text="Weather model type")
    time_point = models.DateTimeField(help_text="Forecast time point")
    forecast_value = models.FloatField(null=True, help_text="Discharge forecast value in m³/s")  

    class Meta:
        verbose_name_plural = "Sector Forecasts"
        indexes = [
            models.Index(fields=['sector', 'model_type', 'time_point']),  
        ]
        unique_together = [['sector', 'model_type', 'time_point']]

    def __str__(self):
        return f"{self.sector.sec_name} - {self.model_type} - {self.time_point}"
    


# 10. Water bodies model
class WaterBodies(models.Model):
    """Model representing water bodies (lakes, rivers, etc.)."""
    fid = models.FloatField(help_text="Feature ID")
    af_wtr_id = models.FloatField(help_text="Africa water body ID")
    sqkm = models.FloatField(help_text="Area in square kilometers")
    name_of_wa = models.CharField(max_length=254, blank=True, null=True, help_text="Water body name")
    type_of_wa = models.CharField(max_length=254, blank=True, null=True, help_text="Water body type")
    shape_area = models.FloatField(help_text="Shape area")
    shape_len = models.FloatField(help_text="Shape length")
    geom = models.MultiPolygonField(srid=4326)

    def __str__(self):
        return self.name_of_wa or f"Water Body {self.af_wtr_id}"

    class Meta:
        verbose_name_plural = "Water Bodies"
        indexes = [
            models.Index(fields=['type_of_wa']),
        ]



# 11. River section model
class RiverSection(models.Model):
    """Model representing river sections with time series data.
    
    Stores discharge simulation data from different weather models
    along with section metadata and thresholds.
    """
    section_name = models.CharField(max_length=100, help_text="River section name")
    time_restart = models.DateTimeField(help_text="Model restart time")
    time_run = models.DateTimeField(help_text="Model run time")
    time_start = models.DateTimeField(help_text="Simulation start time")
    time_series_discharge_simulated_gfs = models.TextField(help_text="GFS discharge time series data (JSON)")
    time_series_discharge_simulated_icon = models.TextField(help_text="ICON discharge time series data (JSON)")
    time_period = models.TextField(help_text="Time period array (JSON)")
    sec_code = models.IntegerField(help_text="Section code")
    sec_name = models.CharField(max_length=100, help_text="Section name")
    basin = models.CharField(max_length=50, help_text="River basin")
    domain = models.CharField(max_length=50, help_text="Domain")
    area = models.FloatField(help_text="Catchment area in sq km")
    latitude = models.FloatField(help_text="Latitude")
    longitude = models.FloatField(help_text="Longitude")
    q_thr1 = models.FloatField(help_text="Discharge threshold level 1")
    q_thr2 = models.FloatField(help_text="Discharge threshold level 2")
    q_thr3 = models.FloatField(help_text="Discharge threshold level 3")
    category = models.CharField(max_length=50, null=True, blank=True, help_text="Section category")
    geometry = models.PointField(srid=4326)

    def __str__(self):
        return f"{self.section_name} - {self.time_run}"

    class Meta:
        verbose_name_plural = "River Sections"
        indexes = [
            models.Index(fields=['sec_code', 'time_run']),
            models.Index(fields=['basin']),
        ]
    


# 12. Administrative boundary level 1 model
class Admin1(models.Model):
    """Model representing administrative level 1 boundaries."""
    objectid = models.BigIntegerField(help_text="Object ID")
    country = models.CharField(max_length=254, help_text="Country name")
    area = models.FloatField(help_text="Area in sq km")
    shape_leng = models.FloatField(help_text="Shape perimeter length")
    shape_area = models.FloatField(help_text="Shape area")
    land_under = models.CharField(max_length=254, null=True, blank=True, help_text="Land under administration")
    geom = models.MultiPolygonField(srid=4326)

    def __str__(self):
        return self.country
    
    class Meta:
        verbose_name_plural = "Administrative Level 1"  

