
# from django.db import models
from django.contrib.gis.db import models 
from django.db import models as django_models
from django.contrib.postgres.fields import JSONField
from django.utils import timezone


# Removed old impact layer models (BaseImpactModel, BaseImpactForecastModel, and 14 total impact models)

# Base raster model for TIFF data
class BaseRasterModel(models.Model):
    """Abstract base model for raster data with date tracking."""
    
    data_date = models.DateField(help_text="Date of the raster data")
    time_run = models.CharField(max_length=4, default="00", help_text="Run time (00, 06, 12, 18)")
    raster = models.RasterField(null=True, blank=True, help_text="Raster data as COG")
    file_path = models.CharField(max_length=500, help_text="Original file path")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['data_date', 'time_run']),
            models.Index(fields=['data_date']),
        ]


class AlertLevelRaster(BaseRasterModel):
    """Model for storing alert level raster data as COG."""
    
    ALERT_GROUPS = [
        ('group1', 'Group 1'),
        ('group2', 'Group 2'), 
        ('group4', 'Group 4'),
    ]
    
    alert_group = models.CharField(
        max_length=10, 
        choices=ALERT_GROUPS,
        help_text="Alert group (group1, group2, group4)"
    )
    
    class Meta:
        verbose_name_plural = "Alert Level Rasters"
        unique_together = ['data_date', 'time_run', 'alert_group']
        indexes = [
            models.Index(fields=['data_date', 'alert_group']),
            models.Index(fields=['alert_group']),
        ]
    
    def __str__(self):
        return f"Alert Level {self.alert_group} - {self.data_date} {self.time_run}"


class FloodHazardMapRaster(BaseRasterModel):
    """Model for storing flood hazard map raster data as COG."""
    
    class Meta:
        verbose_name_plural = "Flood Hazard Map Rasters"
        unique_together = ['data_date', 'time_run']
        indexes = [
            models.Index(fields=['data_date']),
        ]
    
    def __str__(self):
        return f"Flood Hazard Map - {self.data_date} {self.time_run}"


# Base IBEW v2 model
# Removed IBEW v2 models (BaseIBEWv2Model and 5 impact models)

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
    


# 12. Administrative boundary level 0 model (Country boundaries)
class Admin0(models.Model):
    """Model representing administrative level 0 (country) boundaries."""
    objectid_1 = models.BigIntegerField(null=True, blank=True, help_text="Object ID 1")
    fid_1 = models.FloatField(null=True, blank=True, help_text="Feature ID")
    gid_0 = models.CharField(max_length=10, null=True, blank=True, help_text="Global ID (country code)")
    country = models.CharField(max_length=254, null=True, blank=True, help_text="Country name")
    objectid = models.BigIntegerField(null=True, blank=True, help_text="Object ID")
    shape_leng = models.FloatField(null=True, blank=True, help_text="Shape perimeter length")
    shape_le_1 = models.FloatField(null=True, blank=True, help_text="Shape length 1")
    shape_area = models.FloatField(null=True, blank=True, help_text="Shape area")
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.country or f"Country {self.gid_0}"

    class Meta:
        db_table = 'Impact_admin0'
        verbose_name = "Administrative Level 0 (Country)"
        verbose_name_plural = "Administrative Level 0 (Countries)"


# 13. Administrative boundary level 1 model
class Admin1(models.Model):
    """Model representing administrative level 1 boundaries."""
    objectid = models.BigIntegerField(null=True, blank=True, help_text="Object ID")
    country = models.CharField(max_length=254, null=True, blank=True, help_text="Country name")
    area = models.FloatField(null=True, blank=True, help_text="Area in sq km")
    shape_leng = models.FloatField(null=True, blank=True, help_text="Shape perimeter length")
    shape_area = models.FloatField(null=True, blank=True, help_text="Shape area")
    land_under = models.CharField(max_length=254, null=True, blank=True, help_text="Land under administration")
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True)

    def __str__(self):
        return self.country

    class Meta:
        verbose_name_plural = "Administrative Level 1"  




# 14. HydroRIVERS (Static data - loaded once from HydroRIVERS_v10_GHA.geojson)
class HydroRivers(models.Model):
    """Model for storing HydroRIVERS v10 river network data.

    Based on HydroRIVERS_v10_GHA.geojson containing 283,806 river segments.
    """
    hyriv_id = models.BigIntegerField(unique=True, help_text="HydroRIVERS unique identifier")
    next_down = models.BigIntegerField(help_text="ID of next downstream river segment")
    main_riv = models.BigIntegerField(help_text="ID of the main river")
    length_km = models.FloatField(help_text="Length of river segment in kilometers")
    dist_dn_km = models.FloatField(help_text="Distance to downstream point in kilometers")
    dist_up_km = models.FloatField(help_text="Distance to upstream point in kilometers")
    catch_skm = models.FloatField(help_text="Catchment area in square kilometers")
    upland_skm = models.FloatField(help_text="Upland area in square kilometers")
    endorheic = models.IntegerField(default=0, help_text="Endorheic basin indicator (0 or 1)")
    dis_av_cms = models.FloatField(help_text="Average discharge in cubic meters per second")
    ord_stra = models.IntegerField(help_text="Strahler stream order")
    ord_clas = models.IntegerField(help_text="Classic stream order")
    ord_flow = models.IntegerField(help_text="Flow-based stream order")
    hybas_l12 = models.BigIntegerField(help_text="HydroBASINS level 12 ID")
    geometry = models.MultiLineStringField(srid=4326, help_text="River segment geometry")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"River {self.hyriv_id}"

    class Meta:
        verbose_name = "HydroRIVERS River"
        verbose_name_plural = "HydroRIVERS Rivers"
        indexes = [
            models.Index(fields=['hyriv_id']),
            models.Index(fields=['ord_stra']),
            models.Index(fields=['dis_av_cms']),
        ]


# 15. Monitoring Stations (Extracted from GeoJSON for WFS)
class MonitoringStation(models.Model):
    """Model for storing monitoring station points with proper geometry for MapServer WFS."""
    
    # Station identification
    sec_name = models.CharField(max_length=100, help_text="Station name")
    sec_code = models.IntegerField(help_text="Station code")
    basin = models.CharField(max_length=50, help_text="River basin")
    station_type = models.CharField(max_length=20, help_text="Station type")
    
    # Administrative info
    admin_b_l1 = models.CharField(max_length=100, null=True, blank=True, help_text="Admin boundary level 1")
    domain = models.CharField(max_length=50, help_text="Domain")
    
    # Thresholds
    q_thr1 = models.FloatField(help_text="Alert threshold")
    q_thr2 = models.FloatField(help_text="Alarm threshold")
    q_thr3 = models.FloatField(help_text="Emergency threshold")
    
    # Geographic data
    area = models.FloatField(help_text="Catchment area")
    geometry = models.PointField(srid=4326, help_text="Station location")
    
    # Data linkage
    latest_data_date = models.DateField(help_text="Latest available data date")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.sec_name} ({self.sec_code})"
    
    class Meta:
        verbose_name_plural = "Monitoring Stations"
        unique_together = [['sec_name', 'sec_code']]
        indexes = [
            models.Index(fields=['sec_code']),
            models.Index(fields=['basin']),
            models.Index(fields=['domain']),
            models.Index(fields=['latest_data_date']),
        ]


# 16. Merged Deterministic GeoJSON Storage
class MergedDeterministicGeoJSON(models.Model):
    """Model for storing complete merged deterministic forecast GeoJSON files.
    
    Stores the entire merged GeoJSON as a single record per day,
    containing all 979 features with their geometries and properties.
    """
    
    # Date identification
    data_date = models.DateField(unique=True, help_text="Date of the merged data (YYYY-MM-DD)")
    date_string = models.CharField(max_length=8, unique=True, help_text="Date string (YYYYMMDD)")
    
    # GeoJSON content
    geojson_data = models.JSONField(help_text="Complete GeoJSON FeatureCollection")
    
    # Metadata
    feature_count = models.IntegerField(help_text="Number of features in the GeoJSON")
    file_count = models.IntegerField(help_text="Number of source JSON files processed")
    
    # File reference
    file_path = models.CharField(max_length=500, null=True, blank=True, help_text="Path to the GeoJSON file")
    
    # Processing metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.CharField(max_length=100, default="merge_deterministic_forecast", help_text="Processing script/user")
    
    def __str__(self):
        return f"Merged GeoJSON - {self.data_date} ({self.feature_count} features)"
    
    class Meta:
        verbose_name = "Merged Deterministic GeoJSON"
        verbose_name_plural = "Merged Deterministic GeoJSON Files"
        ordering = ['-data_date']
        indexes = [
            models.Index(fields=['data_date']),
            models.Index(fields=['date_string']),
            models.Index(fields=['created_at']),
        ]


class GeoSFMForecastGeoJSON(models.Model):
    """Model for storing GeoSFM hydrological forecast GeoJSON files.

    Stores the merged GeoSFM forecast data (riverdepth and streamflow)
    merged with forecast location points as a single GeoJSON per date.
    Output is saved to frontend/public/ for direct frontend consumption.
    """

    # Date identification
    data_date = models.DateField(unique=True, help_text="Date of the forecast data (YYYY-MM-DD)")
    date_string = models.CharField(max_length=8, unique=True, help_text="Date string (YYYYMMDD)")

    # GeoJSON content
    geojson_data = models.JSONField(help_text="Complete GeoJSON FeatureCollection with forecast locations and values")

    # Metadata
    feature_count = models.IntegerField(help_text="Number of features (forecast locations)")
    matched_count = models.IntegerField(help_text="Number of locations with matched GeoSFM data")
    zones_processed = models.IntegerField(default=6, help_text="Number of zones processed")

    # File references
    file_path = models.CharField(max_length=500, null=True, blank=True, help_text="Path to the GeoJSON file in frontend/public/")
    gcs_source_prefix = models.CharField(max_length=200, default="geosfm_output_icpac_pc/", help_text="GCS bucket source prefix")

    # Processing metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.CharField(max_length=100, default="load_geosfm_data", help_text="Processing command/user")

    # Statistics (optional)
    riverdepth_min = models.FloatField(null=True, blank=True, help_text="Minimum river depth value")
    riverdepth_max = models.FloatField(null=True, blank=True, help_text="Maximum river depth value")
    streamflow_min = models.FloatField(null=True, blank=True, help_text="Minimum streamflow value")
    streamflow_max = models.FloatField(null=True, blank=True, help_text="Maximum streamflow value")

    def __str__(self):
        return f"GeoSFM Forecast - {self.data_date} ({self.matched_count}/{self.feature_count} locations)"

    class Meta:
        verbose_name = "GeoSFM Forecast GeoJSON"
        verbose_name_plural = "GeoSFM Forecast GeoJSON Files"
        ordering = ['-data_date']
        indexes = [
            models.Index(fields=['data_date']),
            models.Index(fields=['date_string']),
            models.Index(fields=['created_at']),
        ]


class EnsembleForecastGeoJSON(models.Model):
    """Model for storing Ensemble hydrological forecast GeoJSON files.

    Stores merged ensemble forecast data (riverdepth and streamflow) from FTP Zone*.csv files,
    merged with EnsembleControlPoint locations as a single GeoJSON per date.

    This is separate from GeoSFMForecastGeoJSON which stores satellite-based flood detection data.
    """

    # Date identification
    data_date = models.DateField(unique=True, help_text="Date of the forecast data (YYYY-MM-DD)")
    date_string = models.CharField(max_length=8, unique=True, help_text="Date string (YYYYMMDD)")

    # GeoJSON content
    geojson_data = models.JSONField(help_text="Complete GeoJSON FeatureCollection with ensemble forecast locations and values")

    # Metadata
    feature_count = models.IntegerField(help_text="Number of features (forecast locations)")
    matched_count = models.IntegerField(help_text="Number of locations with matched ensemble data")
    zones_processed = models.IntegerField(default=0, help_text="Number of zones processed from FTP")

    # Processing metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.CharField(max_length=100, default="sync_ensemble_ftp", help_text="Processing command/user")

    # Statistics (optional)
    riverdepth_min = models.FloatField(null=True, blank=True, help_text="Minimum river depth value")
    riverdepth_max = models.FloatField(null=True, blank=True, help_text="Maximum river depth value")
    riverdepth_avg = models.FloatField(null=True, blank=True, help_text="Average river depth value")
    streamflow_min = models.FloatField(null=True, blank=True, help_text="Minimum streamflow value")
    streamflow_max = models.FloatField(null=True, blank=True, help_text="Maximum streamflow value")
    streamflow_avg = models.FloatField(null=True, blank=True, help_text="Average streamflow value")

    def __str__(self):
        return f"Ensemble Forecast - {self.data_date} ({self.matched_count}/{self.feature_count} locations)"

    class Meta:
        verbose_name = "Ensemble Forecast GeoJSON"
        verbose_name_plural = "Ensemble Forecast GeoJSON Files"
        ordering = ['-data_date']
        indexes = [
            models.Index(fields=['data_date']),
            models.Index(fields=['date_string']),
            models.Index(fields=['created_at']),
        ]


class Admin2(models.Model):
    """Admin Level 2 boundaries model"""
    objectid = models.BigIntegerField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    adm1_name = models.CharField(max_length=100, null=True, blank=True)
    adm2_name = models.CharField(max_length=100, null=True, blank=True)
    area = models.FloatField(null=True, blank=True)
    shape_leng = models.FloatField(null=True, blank=True)
    shape_area = models.FloatField(null=True, blank=True)
    land_under = models.CharField(max_length=100, null=True, blank=True)
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True)

    def __str__(self):
        return f"{self.country} - {self.adm1_name} - {self.adm2_name}"

    class Meta:
        db_table = 'Impact_admin2'
        verbose_name = "Admin Level 2 Boundary"
        verbose_name_plural = "Admin Level 2 Boundaries"


class EnsembleControlPoint(models.Model):
    """Model for storing ensemble control points used for merging forecast data.

    These control points are used as reference locations for merging ensemble forecast
    data with other CSV or forecast datasets. Each point has a unique ID, GRIDCODE,
    and zone information for spatial matching.
    """

    # Unique identifiers
    point_id = models.IntegerField(unique=True, help_text="Unique point ID")
    gridcode = models.IntegerField(db_index=True, help_text="Grid code for spatial matching")

    # Location data
    admin_name = models.CharField(max_length=254, null=True, blank=True, help_text="Administrative region name")
    x = models.FloatField(help_text="Longitude coordinate")
    y = models.FloatField(help_text="Latitude coordinate")

    # Zone information
    zone = models.IntegerField(db_index=True, help_text="Zone number (e.g., 6 for Zone 6)")

    # Node flag
    is_node = models.BooleanField(default=True, help_text="Whether this point is a node")

    # Geometry
    geom = models.PointField(srid=4326, help_text="Point geometry")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Control Point {self.point_id} - {self.admin_name or 'Unknown'} (GRIDCODE: {self.gridcode})"

    class Meta:
        db_table = 'impact_ensemble_control_point'
        verbose_name = "Ensemble Control Point"
        verbose_name_plural = "Ensemble Control Points"
        ordering = ['point_id']
        indexes = [
            models.Index(fields=['point_id']),
            models.Index(fields=['gridcode']),
            models.Index(fields=['zone']),
            models.Index(fields=['admin_name']),
        ]


class EnsembleForecastGeoJSON(models.Model):
    """Model for storing merged ensemble forecast GeoJSON files.

    Stores the complete merged GeoJSON with ensemble control points
    and their associated forecast data from Combined CSV files.
    Each record contains all 3,199 features with embedded forecast time series.
    """

    # Date identification - using the latest forecast date in the dataset
    data_date = models.DateField(unique=True, help_text="Date of the forecast data (YYYY-MM-DD)")
    date_string = models.CharField(max_length=8, unique=True, help_text="Date string (YYYYMMDD)")

    # GeoJSON content
    geojson_data = models.JSONField(help_text="Complete GeoJSON FeatureCollection with forecast data")

    # Metadata
    feature_count = models.IntegerField(help_text="Total number of features (control points)")
    features_with_data = models.IntegerField(help_text="Number of features with forecast data")
    features_without_data = models.IntegerField(help_text="Number of features missing forecast data")

    # File reference
    file_path = models.CharField(max_length=500, default="backend/static_data/ensemble_with_forecasts.geojson",
                                help_text="Path to the merged GeoJSON file")

    # Processing metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.CharField(max_length=100, default="load_ensemble_forecast",
                                   help_text="Processing command/user")

    def __str__(self):
        return f"Ensemble Forecast - {self.data_date} ({self.features_with_data}/{self.feature_count} with data)"

    class Meta:
        db_table = 'impact_ensemble_forecast_geojson'
        verbose_name = "Ensemble Forecast GeoJSON"
        verbose_name_plural = "Ensemble Forecast GeoJSON Files"
        ordering = ['-data_date']
        indexes = [
            models.Index(fields=['data_date']),
            models.Index(fields=['date_string']),
            models.Index(fields=['created_at']),
        ]


# Import report workflow models
from .models_reports import StationReportApproval, StationAssessment, SavedReport

from .models_layer_config import MapLayerConfig
