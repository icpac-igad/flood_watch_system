from adminboundarymanager.models import AdminBoundarySettings
from django.conf import settings
from django.urls import reverse
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from wagtail.api.v2.utils import get_full_url as wagtail_get_full_url
from urllib.parse import urljoin

from geomanager.models import Category, VectorLayerIcon, VectorTileLayerIcon, GeomanagerSettings, Dataset
from geomanager.serializers import CategorySerializer, DatasetSerializer
from home.models import MultimodalClusterSettings


def get_full_url(request, path):
    """
    Custom get_full_url that uses CMS_BASE_URL environment variable when available.
    Falls back to Wagtail's default behavior if CMS_BASE_URL is not set.
    """
    cms_base_url = getattr(settings, 'CMS_BASE_URL', None)
    if cms_base_url:
        # Ensure path starts with /
        if path and not path.startswith('/'):
            path = '/' + path
        return urljoin(cms_base_url, path)
    return wagtail_get_full_url(request, path)


@api_view(['GET'])
@renderer_classes([JSONRenderer])
def get_mapviewer_config(request):
    """Custom mapviewer config that includes datasets and layers"""
    gm_settings = GeomanagerSettings.for_request(request)
    abm_settings = AdminBoundarySettings.for_request(request)

    categories = Category.objects.all()
    categories_data = CategorySerializer(categories, many=True).data

    # Add datasets with layers
    datasets = Dataset.objects.filter(published=True)
    datasets_data = DatasetSerializer(datasets, many=True, context={"request": request}).data

    response = {
        "categories": categories_data,
        "datasets": datasets_data,  # Add datasets to response
        "enableMyAccount": False,
        "allowSignups": False,
    }

    if gm_settings.enable_my_account:
        response.update({
            "enableMyAccount": True,
        })

    if gm_settings.allow_signups:
        response.update({
            "allowSignups": True,
        })

    if gm_settings.map_disclaimer_text:
        response.update({"disclaimerText": gm_settings.map_disclaimer_text})

    links = {
        "mapViewerBaseUrl": get_full_url(request, (reverse("mapview"))),
    }

    if gm_settings.terms_of_service_page:
        links.update(
            {"termsOfServicePageUrl": get_full_url(request, gm_settings.terms_of_service_page.get_full_url(request))})

    if gm_settings.privacy_policy_page:
        links.update(
            {"privacyPolicyPageUrl": get_full_url(request, gm_settings.privacy_policy_page.get_full_url(request))})

    if gm_settings.map_disclaimer_page:
        links.update({"disclaimerPageUrl": gm_settings.map_disclaimer_page.get_full_url(request)})

    if gm_settings.contact_us_page:
        links.update({"contactUsPageUrl": gm_settings.contact_us_page.get_full_url(request)})

    response.update({"links": links})

    icon_images = []
    for icon in VectorLayerIcon.objects.all():
        icon_images.append({"name": icon.name, "url": get_full_url(request, icon.file.url)})

    for icon in VectorTileLayerIcon.objects.all():
        icon_images.append({"name": icon.name, "url": get_full_url(request, icon.file.url)})

    response.update({"vectorLayerIcons": icon_images})

    if gm_settings.logo:
        logo = {
            "imageUrl": get_full_url(request, gm_settings.logo.file.url)
        }

        if gm_settings.logo_page:
            logo.update({"linkUrl": get_full_url(request, gm_settings.logo_page.url)})

        if not gm_settings.logo_page and gm_settings.logo_external_link:
            logo.update({"linkUrl": gm_settings.logo_external_link, "external": True})

        response.update({"logo": logo})

    if abm_settings.countries_list:
        response.update({
            "countries": abm_settings.countries_list,
            "bounds": abm_settings.combined_countries_bounds,
            "boundaryDataSource": abm_settings.data_source
        })

    base_maps_data = []

    tile_gl_source = gm_settings.tile_gl_source

    if tile_gl_source:
        # get base maps
        for base_map in gm_settings.base_maps:
            data = base_map.block.get_api_representation(base_map.value)
            for key, value in base_map.value.items():
                if key == "image" and value:
                    data.update({"image": get_full_url(request, value.file.url)})

            data.update({"mapStyle": get_full_url(request, tile_gl_source.map_style_url)})
            base_maps_data.append(data)

    response.update({"basemaps": base_maps_data})

    # Add multimodal cluster settings
    try:
        cluster_settings = MultimodalClusterSettings.load(request_or_site=request)
        response.update({"multimodalClusterConfig": cluster_settings.get_config()})
    except Exception:
        # Settings not configured - cluster layer will use its own defaults
        pass

    # Add boundary layer config
    response.update({
        "boundaryLayerConfig": {
            "default": {
                "admin0": "b6c3b7d9-c3dd-4012-9cc9-857f0640e702",
                "admin1": "02453614-2716-4ca3-bc82-589b364fe47e",
                "admin2": "c47279f5-8481-4529-86f3-f58810f7d567",
            },
        }
    })

    # Add multimodal layer URL config
    response.update({
        "multimodalLayerConfig": {
            "default": {
                "baseUrl": "/pg/tileserv/gha.multimodal_points_clustered/{z}/{x}/{y}.pbf",
                "sourceLayer": "gha.multimodal_points_clustered",
            },
        }
    })

    return Response(response)
