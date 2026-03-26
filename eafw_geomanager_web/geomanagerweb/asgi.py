import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django_nextjs.asgi import NextJsMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geomanagerweb.settings.production")
django_asgi_app = get_asgi_application()

websocket_routers = []

application = NextJsMiddleware(
    ProtocolTypeRouter(
        {
            # Django's ASGI application to handle traditional HTTP and websocket requests.
            "http": django_asgi_app,
            "websocket": AuthMiddlewareStack(URLRouter(websocket_routers)),
        }
    )
)
