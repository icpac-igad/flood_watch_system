from django.utils.translation import gettext_lazy as _

DEFAULT_RASTER_MAX_UPLOAD_SIZE_MB = 100

DATASET_USE_MODE = (("historical", _("Monitoring Dataset")), ("prediction", _("Forecasting Dataset")))

DATASET_TYPE_CHOICES = (
    ("raster_file", _("Raster File - NetCDF/GeoTiff")),
    ("vector_file", _("Vector File - Shapefile, Geojson")),
    ("wms", _("Web Map Service - WMS Layer")),
    ("raster_tile", _("XYZ Raster Tile Layer")),
    ("vector_tile", _("XYZ Vector Tile Layer")),
)

CURRENT_TIME_METHOD_CHOICES = (
    ("latest_from_source", _("Latest available date from source")),
    ("earliest_from_source", _("Earliest available date from source")),
    ("previous_to_now", _("Date previous to current date time")),
    ("next_to_now", _("Date next to current date time")),
    ("from_dataset_props", _("Dataset model property set by data ingestion job")),
)

DATE_FORMAT_CHOICES = (
    ("yyyy-MM-dd HH:mm", _("Hour minute:second - (E.g 2023-01-01 00:00)")),
    ("yyyy-MM-dd", _("Day - (E.g 2023-01-01)")),
    ("pentadal", _("Pentadal - (E.g Jan 2023 - P1 1-5th)")),
    ("dekadal", _("Dekadal - (E.g Jan 2023 - D1 1-10th)")),
    ("yyyy-MM", _("Month number - (E.g 2023-01)")),
    ("MMMM yyyy", _("Month name - (E.g January 2023)")),
    ("yyyy", _("Year - (E.g 2023)")),
)

JS_TO_PYTHONIC_DATE_FORMAT_CHOICES = {
    "yyyy-MM-dd HH:mm": "%Y-%m-%d %H:%M",
    "yyyy-MM-dd": "%Y-%m-%d",
    "yyyy-MM": "%Y-%m",
    "MMMM yyyy": "%B %Y",
    "yyyy": "%Y",
}


PARSER_TYPE_CHOICES = [
    ("direct_date_field", _("Direct Date Field")),
    ("multi_field_constructor", _("Multi-Field Date Constructor")),
]

PERIOD_TYPE_CHOICES = [
    ("daily", _("Daily data product (product updated every day)")),
    ("weekly", _("Weekly data product (updated every week)")),
    ("dekadal", _("Dekadal (10-day periods: days 1, 11, 21)")),
    ("pentadal", _("Pentadal (5-day periods: days 1, 6, 11, 16, 21, 26)")),
    ("monthly", _("Monthly data product (updated every month)")),
    ("seasonal", _("Seasonal data product (updated every season)")),
    ("yearly", _("Yearly data product (updated every year)")),
    ("static", _("Static data product (never updated)")),
]

GRID_RESOLUTION_CHOICES = [
    ("0.01dd", _("1km (0.01dd)")),
    ("0.05dd", _("5km (0.05dd)")),
    ("0.1dd", _("10km (0.1dd)")),
    ("0.25dd", _("25km (0.25dd)")),
    ("0.5dd", _("50km (0.5dd)")),
]
