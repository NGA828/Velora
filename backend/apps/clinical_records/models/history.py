from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel

from .choices import GuardianVisibility


class Allergy(UUIDTimeStampedModel):
    class Severity(models.TextChoices):
        MILD = "MILD", "Mild"
        MODERATE = "MODERATE", "Moderate"
        SEVERE = "SEVERE", "Severe"
        UNKNOWN = "UNKNOWN", "Unknown"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RESOLVED = "RESOLVED", "Resolved"
        ENTERED_IN_ERROR = "ENTERED_IN_ERROR", "Entered in error"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="allergies"
    )
    substance = models.CharField(max_length=140)
    reaction = models.CharField(max_length=240, blank=True)
    severity = models.CharField(max_length=12, choices=Severity.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    recorded_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="allergies_recorded",
    )
    guardian_visibility = models.CharField(
        max_length=12,
        choices=GuardianVisibility.choices,
        default=GuardianVisibility.INTERNAL,
    )

    class Meta:
        ordering = ["-recorded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "substance", "status"],
                name="unique_patient_allergy_substance_status",
            )
        ]

    def __str__(self) -> str:
        return f"{self.patient}: {self.substance}"


class MedicalHistoryEntry(UUIDTimeStampedModel):
    class Category(models.TextChoices):
        MEDICAL = "MEDICAL", "Medical"
        SURGICAL = "SURGICAL", "Surgical"
        FAMILY = "FAMILY", "Family"
        SOCIAL = "SOCIAL", "Social"
        OTHER = "OTHER", "Other"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medical_history_entries",
    )
    category = models.CharField(max_length=16, choices=Category.choices)
    title = models.CharField(max_length=180)
    occurred_on = models.DateField(null=True, blank=True)
    description = models.TextField()
    source = models.CharField(max_length=120, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medical_history_recorded",
    )
    guardian_visibility = models.CharField(
        max_length=12,
        choices=GuardianVisibility.choices,
        default=GuardianVisibility.INTERNAL,
    )

    class Meta:
        ordering = ["-occurred_on", "-created_at"]

    def __str__(self) -> str:
        return self.title
