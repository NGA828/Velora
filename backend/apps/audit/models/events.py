from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class AuditEvent(UUIDTimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=120, db_index=True)
    object_type = models.CharField(max_length=120, db_index=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    before_snapshot = models.JSONField(default=dict, blank=True)
    after_snapshot = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["object_type", "object_id", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.action}: {self.object_type}/{self.object_id}"
