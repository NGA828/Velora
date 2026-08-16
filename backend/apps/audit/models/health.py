from django.db import models

from apps.common.models import UUIDTimeStampedModel


class SystemHeartbeat(UUIDTimeStampedModel):
    service = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=24, default="HEALTHY")
    last_seen_at = models.DateTimeField(db_index=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["service"]

    def __str__(self) -> str:
        return f"{self.service}: {self.status}"
