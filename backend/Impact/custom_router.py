from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.decorators import api_view
from collections import OrderedDict

class RelativeURLRouter(DefaultRouter):
    def get_api_root_view(self, api_urls=None):
        """
        Return a basic root view that returns relative URLs instead of absolute ones.
        """
        api_urls = api_urls or []

        @api_view(['GET'])
        def api_root(request, format=None):
            """
            API root view that returns relative URLs.
            """
            ret = OrderedDict()
            # Manually build the API URLs as relative paths
            for key, url_name, callback in self.registry:
                ret[key] = f'/api/{key}/'

            return Response(ret)

        return api_root