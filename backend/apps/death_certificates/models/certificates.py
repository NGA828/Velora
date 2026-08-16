from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class DeathCertificate(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        VOID = "VOID", "Void"

    certificate_number = models.CharField(max_length=48, unique=True)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="death_certificates",
    )
    issuing_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="death_certificates_issued",
    )
    death_datetime = models.DateTimeField()
    place_of_death = models.CharField(max_length=180)
    primary_cause = models.TextField()
    contributing_causes = models.TextField(blank=True)
    manner_of_death = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="death_certificates_voided",
        null=True,
        blank=True,
    )
    void_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-death_datetime"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=models.Q(status="ISSUED"),
                name="one_issued_death_certificate_per_patient",
            )
        ]

    def __str__(self) -> str:
        return self.certificate_number
