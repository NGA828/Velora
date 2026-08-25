from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class MedicalRecordAccess(UUIDTimeStampedModel):
    class Action(models.TextChoices):
        LIST = "LIST", "List"
        VIEW = "VIEW", "View"
        PRINT = "PRINT", "Print"
        DOWNLOAD = "DOWNLOAD", "Download"
        ATTACH = "ATTACH", "Attach"
        TRANSMIT = "TRANSMIT", "Transmit"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medical_record_accesses",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medical_record_accesses",
    )
    object_type = models.CharField(max_length=120)
    object_id = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=12, choices=Action.choices)
    purpose = models.CharField(max_length=180, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["patient", "user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user} {self.action} {self.object_type} for {self.patient}"
