from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class Notification(UUIDTimeStampedModel):
    class Severity(models.TextChoices):
        INFORMATION = "INFORMATION", "Information"
        SUCCESS = "SUCCESS", "Success"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_triggered",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="notifications",
    )
    category = models.CharField(max_length=80, db_index=True)
    severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
        default=Severity.INFORMATION,
        db_index=True,
    )
    title = models.CharField(max_length=180)
    body = models.CharField(max_length=500)
    route = models.CharField(max_length=300, blank=True)
    data = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=180, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "dedupe_key"],
                condition=~models.Q(dedupe_key=""),
                name="unique_notification_dedupe_per_recipient",
            )
        ]
        indexes = [models.Index(fields=["recipient", "read_at", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.recipient}: {self.title}"
