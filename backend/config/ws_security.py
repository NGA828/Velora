"""WebSocket origin/host validation.

Channels' built-in ``AllowedHostsOriginValidator`` matches ``ALLOWED_HOSTS``
with exact string comparison, which rejects wildcard subdomain entries such as
``.e2b.app`` and any host carrying a non-standard port (e.g. ``127.0.0.1:8000``
from a local client). Django's own host validation understands leading-dot
wildcards, so we mirror that behaviour here so the realtime WebSocket works on
localhost and on the ``*.e2b.app`` preview hosts without weakening the check.
"""

from urllib.parse import urlparse

from django.conf import settings
from channels.exceptions import DenyConnection


def _host_allowed(host: str | None) -> bool:
    if not host:
        return False
    # Drop any port component before comparing against ALLOWED_HOSTS.
    host = host.split(":", 1)[0]
    if host in settings.ALLOWED_HOSTS:
        return True
    return any(
        allowed.startswith(".") and (host == allowed[1:] or host.endswith(allowed))
        for allowed in settings.ALLOWED_HOSTS
    )


class VeloraOriginValidator:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            await self.application(scope, receive, send)
            return
        origin = None
        host = None
        for name, value in scope.get("headers", []):
            if name == b"origin":
                origin = value.decode("latin1")
            elif name == b"host":
                host = value.decode("latin1")
        if self._valid_origin(origin) and self._valid_host(host):
            await self.application(scope, receive, send)
            return
        raise DenyConnection("Invalid origin/host.")

    def _valid_origin(self, origin: str | None) -> bool:
        if not origin:
            return False
        parsed = urlparse(origin)
        return _host_allowed(parsed.hostname or "")

    def _valid_host(self, host: str | None) -> bool:
        return _host_allowed(host)
