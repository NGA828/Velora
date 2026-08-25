from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class MedicalFileAttachment(UUIDTimeStampedModel):
    """A document (report, image, PDF) attached to a patient's medical file by
    a clinician. Uploaded files are also included in the authorized medical
    transfer package emailed to the destination hospital."""

    medical_file = models.ForeignKey(
        "clinical_records.MedicalFile",
        on_delete=models.PROTECT,
        related_name="attachments",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medical_file_attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medical_file_uploads",
    )
    file = models.FileField(upload_to="medical_file_attachments/")
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    byte_size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    description = models.CharField(max_length=300, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.patient})"
