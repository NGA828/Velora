"""ASGI entry point for HTTP and authenticated WebSocket traffic."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from config.websocket import websocket_urlpatterns  # noqa: E402
from config.ws_security import VeloraOriginValidator  # noqa: E402

django_asgi_application = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": VeloraOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
