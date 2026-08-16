from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel

from .choices import GuardianVisibility


class Diagnosis(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PROVISIONAL = "PROVISIONAL", "Provisional"
        CONFIRMED = "CONFIRMED", "Confirmed"
        RESOLVED = "RESOLVED", "Resolved"
        ENTERED_IN_ERROR = "ENTERED_IN_ERROR", "Entered in error"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="diagnoses"
    )
    care_episode = models.ForeignKey(
        "patients.CareEpisode",
        on_delete=models.PROTECT,
        related_name="diagnoses",
        null=True,
        blank=True,
    )
    condition = models.ForeignKey(
        "hospital.ClinicalCondition",
        on_delete=models.PROTECT,
        related_name="diagnoses",
        null=True,
        blank=True,
    )
    code_snapshot = models.CharField(max_length=80)
    name_snapshot = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PROVISIONAL, db_index=True
    )
    diagnosed_at = models.DateTimeField()
    diagnosed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="diagnoses_authored",
    )
    guardian_visibility = models.CharField(
        max_length=12,
        choices=GuardianVisibility.choices,
        default=GuardianVisibility.INTERNAL,
    )

    class Meta:
        ordering = ["-diagnosed_at"]

    def __str__(self) -> str:
        return self.name_snapshot


class TreatmentPlan(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="treatment_plans"
    )
    care_episode = models.ForeignKey(
        "patients.CareEpisode",
        on_delete=models.PROTECT,
        related_name="treatment_plans",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=180)
    objectives = models.TextField(blank=True)
    instructions = models.TextField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    authored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="treatment_plans_authored",
    )
    guardian_visibility = models.CharField(
        max_length=12,
        choices=GuardianVisibility.choices,
        default=GuardianVisibility.INTERNAL,
    )

    class Meta:
        ordering = ["-starts_on", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__isnull=True)
                | models.Q(ends_on__gte=models.F("starts_on")),
                name="treatment_plan_end_after_start",
            )
        ]

    def __str__(self) -> str:
        return self.title
