"""ASGI entry point for HTTP and authenticated WebSocket traffic."""

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env from the repository root before Django settings are imported.

    ``override=False`` lets real OS/PaaS environment variables win over the
    .env file, so the same code works for both local dev and production.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return  # python-dotenv is a dev-only dependency; skip silently in prod

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


_load_dotenv()
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
