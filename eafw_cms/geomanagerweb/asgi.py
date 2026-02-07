import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import re_path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geomanagerweb.settings.production")
django_asgi_app = get_asgi_application()

# Import after get_asgi_application() to ensure Django is set up
try:
    from django_nextjs.proxy import NextJSProxyHttpConsumer, NextJSProxyWebsocketConsumer

    websocket_routers = [
    re_path(r"^(?:_next|__nextjs).*", NextJSProxyWebsocketConsumer.as_asgi()),
    ]
except ImportError:
    websocket_routers = []

application = ProtocolTypeRouter(
{
# Django's ASGI application to handle traditional HTTP and websocket requests.
"http": django_asgi_app,
"websocket": AuthMiddlewareStack(URLRouter(websocket_routers)),
}
)