from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class MedicalFile(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

    patient = models.OneToOneField(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medical_file",
    )
    file_number = models.CharField(max_length=40, unique=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    opened_at = models.DateTimeField()
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medical_files_opened",
    )

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self) -> str:
        return self.file_number
