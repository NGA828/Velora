from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.messaging.realtime import publish_user_event
from apps.notifications.models import Notification


def notify(
    *,
    recipient,
    category: str,
    title: str,
    body: str,
    actor=None,
    patient=None,
    route: str = "",
    severity: str = Notification.Severity.INFORMATION,
    data: dict | None = None,
    dedupe_key: str = "",
) -> Notification:
    created = True
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                actor=actor,
                patient=patient,
                category=category,
                severity=severity,
                title=title,
                body=body,
                route=route,
                data=data or {},
                dedupe_key=dedupe_key,
                delivered_at=timezone.now(),
            )
    except IntegrityError:
        if not dedupe_key:
            raise
        created = False
        notification = Notification.objects.get(recipient=recipient, dedupe_key=dedupe_key)
    if created:
        transaction.on_commit(
            lambda: publish_user_event(
                user_id=recipient.id,
                event_type="notification.created",
                payload={"notification_id": str(notification.id)},
            )
        )
    return notification
