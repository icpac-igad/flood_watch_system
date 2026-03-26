from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet
from home.models import MapserverConfig

api_router = WagtailAPIRouter("webapi")


class MapserverConfigAPIViewSet(BaseAPIViewSet):
    model = MapserverConfig
    model_fields = [
        "service_title",
        "service_purpose",
        "service_provider",
        "provider_url",
        "contact_name",
        "email_address",
        "office_country",
        "office_city",
        "physical_address",
        "default_language",
        "service_fee",
        "use_terms",
    ]
    # Add model fields to both the listing and detail views
    listing_default_fields = model_fields
    body_fields = model_fields


# Register mapserver config endpoint
api_router.register_endpoint("wms-wfs", MapserverConfigAPIViewSet)
