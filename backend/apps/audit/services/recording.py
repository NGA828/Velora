from __future__ import annotations

import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder

from apps.audit.models import AuditEvent

REDACTED_KEYS = {
    "password",
    "old_password",
    "new_password",
    "token",
    "token_hash",
    "session",
    "secret",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in REDACTED_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(_redact(value), cls=DjangoJSONEncoder))


def _client_ip(request) -> str | None:
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    return candidate or None


def record_audit_event(
    *,
    action: str,
    object_type: str,
    object_id: str = "",
    actor=None,
    request=None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str = "",
) -> AuditEvent:
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        before_snapshot=_json_safe(before or {}),
        after_snapshot=_json_safe(after or {}),
        reason=reason,
        request_id=getattr(request, "request_id", "") if request else "",
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:512] if request else "",
    )
