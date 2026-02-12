import pytz
from urllib.parse import urljoin
from django.conf import settings
from django.conf.global_settings import TIME_ZONE
from geomanager.utils.constants import JS_TO_PYTHONIC_DATE_FORMAT_CHOICES
from rest_framework import serializers

from geomanager.models import Category, SubCategory, Dataset, Metadata
from geomanager.serializers.raster_file import RasterFileLayerSerializer
from geomanager.serializers.raster_tile import RasterTileLayerSerializer
from geomanager.serializers.vector_file import VectorFileLayerSerializer
from geomanager.serializers.vector_tile import VectorTileLayerSerializer
from geomanager.serializers.wms import WmsLayerSerializer


def _get_full_url(request, path: str) -> str:
    """
    Build absolute URLs for API endpoints.

    Prefer CMS_BASE_URL when set (useful behind nginx/reverse proxies),
    otherwise fall back to request.build_absolute_uri.
    """
    cms_base_url = getattr(settings, "CMS_BASE_URL", None)
    if cms_base_url:
        if path and not path.startswith("/"):
            path = "/" + path
        return urljoin(cms_base_url, path)
    if request:
        return request.build_absolute_uri(path)
    return path


def _build_modular_model_layer_config(request, endpoint_path: str) -> dict:
    return {
        "type": "geojson",
        "source": {
            "type": "geojson",
            "data": _get_full_url(request, endpoint_path),
        },
        "render": {
            "layers": [
                {
                    "type": "circle",
                    "paint": {
                        "circle-color": [
                            "match",
                            ["get", "alert_level"],
                            "emergency",
                            "#d32f2f",
                            "alarm",
                            "#ff9800",
                            "warning",
                            "#ffc107",
                            "normal",
                            "#b0b0b0",
                            "#b0b0b0",
                        ],
                        "circle-radius": 5,
                        "circle-opacity": 0.85,
                        "circle-stroke-color": "#ffffff",
                        "circle-stroke-width": 1.2,
                    },
                    "metadata": {"position": "top"},
                }
            ]
        },
    }


class DatasetSerializer(serializers.ModelSerializer):
    layers = serializers.SerializerMethodField()
    layer = serializers.SerializerMethodField()
    dataset = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    isMultiLayer = serializers.SerializerMethodField()
    initialVisible = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "id",
            "dataset",
            "name",
            "capabilities",
            "summary",
            "layer",
            "dataset_slug",
            "latest_date",
            "isMultiLayer",
            "category",
            "sub_category",
            "metadata",
            "layers",
            "initialVisible",
            "public",
            "layer_type",
        ]

    def get_initialVisible(self, obj):
        return obj.initial_visible

    def get_isMultiLayer(self, obj):
        return obj.multi_layer

    def get_capabilities(self, obj):
        return obj.capabilities

    def get_layers(self, obj):
        request = self.context.get("request")

        modular_overrides = {
            # These are placeholder CMS datasets that should render from the
            # modular API endpoints (DB-backed or derived from multimodal tables).
            "GeoSFM Flood Forecast": {
                "endpoint": "/api/geosfm/geojson/",
                "interaction_output": [
                    {"column": "admin_name", "property": "Location", "type": "string"},
                    {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                    {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                    {"column": "alert_level", "property": "Alert Level", "type": "string"},
                    {"column": "daily_avg", "property": "GeoSFM (m³/s)", "type": "number"},
                    {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                    {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                    {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                    {"column": "data_date", "property": "Data Date", "type": "string"},
                    {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                    {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
                ],
            },
            "Mike Hydro": {
                "endpoint": "/api/mike-hydro/geojson/",
                "interaction_output": [
                    {"column": "admin_name", "property": "Location", "type": "string"},
                    {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                    {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                    {"column": "alert_level", "property": "Alert Level", "type": "string"},
                    {"column": "daily_avg", "property": "Mike Hydro (m³/s)", "type": "number"},
                    {"column": "mike_hydro_rfe", "property": "Mike Hydro RFE (m³/s)", "type": "number"},
                    {"column": "mike_hydro_chirp", "property": "Mike Hydro CHIRP (m³/s)", "type": "number"},
                    {"column": "mike_hydro_imerg", "property": "Mike Hydro IMERG (m³/s)", "type": "number"},
                    {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                    {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                    {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                    {"column": "data_date", "property": "Data Date", "type": "string"},
                    {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                    {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
                ],
            },
            "Google Flood Forecast": {
                "endpoint": "/api/google-flood/geojson/",
                "interaction_output": [
                    {"column": "admin_name", "property": "Location", "type": "string"},
                    {"column": "gauge_id", "property": "Gauge ID", "type": "string"},
                    {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                    {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                    {"column": "alert_level", "property": "Alert Level", "type": "string"},
                    {"column": "google_flood_severity", "property": "Google Severity", "type": "string"},
                    {"column": "daily_avg", "property": "Forecast Flow (m³/s)", "type": "number"},
                    {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                    {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                    {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                    {"column": "data_date", "property": "Data Date", "type": "string"},
                    {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                    {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
                ],
            },
            # Floodproofs model-only view (from multimodal forecasts).
            # Note: This intentionally overrides the placeholder dataset config so the Floodproofs
            # subcategory can display the same control points as Multimodal, but showing only the
            # Floodproof model series in the popup chart.
            "Floodproofs Discharge Forecast": {
                "endpoint": "/api/floodproof/geojson/",
                "interaction_output": [
                    {"column": "admin_name", "property": "Location", "type": "string"},
                    {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                    {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                    {"column": "alert_level", "property": "Alert Level", "type": "string"},
                    {"column": "daily_avg", "property": "Floodproofs (m³/s)", "type": "number"},
                    {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                    {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                    {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                    {"column": "data_date", "property": "Data Date", "type": "string"},
                    {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                    {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
                ],
            },
        }

        override = modular_overrides.get(obj.title)

        if obj.layer_type == "raster_file":
            layers_data = RasterFileLayerSerializer(
                obj.raster_file_layers, many=True, context={"request": request}
            ).data

        elif obj.layer_type == "vector_file":
            layers_data = VectorFileLayerSerializer(
                obj.vector_file_layers, many=True, context={"request": request}
            ).data

        elif obj.layer_type == "wms":
            layers_data = WmsLayerSerializer(obj.wms_layers, many=True, context={"request": request}).data

        elif obj.layer_type == "raster_tile":
            layers_data = RasterTileLayerSerializer(
                obj.raster_tile_layers, many=True, context={"request": request}
            ).data

        elif obj.layer_type == "vector_tile":
            layers_data = VectorTileLayerSerializer(
                obj.vector_tile_layers, many=True, context={"request": request}
            ).data

        else:
            layers_data = None

        if not override or not layers_data:
            return layers_data

        endpoint_path = override["endpoint"]
        for layer in layers_data:
            layer["layerConfig"] = _build_modular_model_layer_config(request, endpoint_path)
            layer["interactionConfig"] = {
                "type": "intersection",
                "output": override["interaction_output"],
            }
            layer["params"] = {}
            layer["paramsSelectorConfig"] = []
            layer["multiTemporal"] = False
            layer["layerType"] = "geojson"

        return layers_data

    def get_layer(self, obj):
        return obj.get_default_layer()

    def get_dataset(self, obj):
        return obj.id

    def get_name(self, obj):
        return obj.title


class DatasetDetailSerializer(serializers.ModelSerializer):
    latest_date = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "summary",
            "dataset_slug",
            "latest_date",
            "public",
            "layer_type",
        ]

    def get_latest_date(self, obj) -> str | None:
        local_tz = pytz.timezone(TIME_ZONE)
        if obj.latest_date is not None:
            latest_date = obj.latest_date.astimezone(local_tz)
            date_format = JS_TO_PYTHONIC_DATE_FORMAT_CHOICES[obj.wms_layers.first().date_format]
            return latest_date.strftime(date_format if date_format is not None else "%Y-%m-%d")
        return None

    def get_name(self, obj):
        return obj.title


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    sub_categories = SubCategorySerializer(many=True, read_only=True)
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "title", "icon", "active", "public", "sub_categories"]

    def get_icon(self, obj):
        icon_name = obj.icon
        if not icon_name:
            icon_name = "layer-group"
        return f"icon-{icon_name}"


class MetadataSerialiazer(serializers.ModelSerializer):
    class Meta:
        model = Metadata
        fields = "__all__"
