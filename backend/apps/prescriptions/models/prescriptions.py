from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class Prescription(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="prescriptions",
    )
    care_episode = models.ForeignKey(
        "patients.CareEpisode",
        on_delete=models.PROTECT,
        related_name="prescriptions",
    )
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="prescriptions_authored",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    prescribed_at = models.DateTimeField()
    starts_on = models.DateField()
    ends_on = models.DateField()
    clinical_instructions = models.TextField(blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-prescribed_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F("starts_on")),
                name="prescription_end_not_before_start",
            )
        ]
        indexes = [models.Index(fields=["patient", "status", "-prescribed_at"])]

    def __str__(self) -> str:
        return f"{self.patient} — {self.prescribed_at:%Y-%m-%d}"


class PrescriptionItem(UUIDTimeStampedModel):
    class Route(models.TextChoices):
        ORAL = "ORAL", "Oral"
        INTRAVENOUS = "INTRAVENOUS", "Intravenous"
        INTRAMUSCULAR = "INTRAMUSCULAR", "Intramuscular"
        SUBCUTANEOUS = "SUBCUTANEOUS", "Subcutaneous"
        TOPICAL = "TOPICAL", "Topical"
        INHALATION = "INHALATION", "Inhalation"
        OTHER = "OTHER", "Other"

    class ScheduleType(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        PRN = "PRN", "As needed (PRN)"

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.PROTECT,
        related_name="items",
    )
    medication = models.ForeignKey(
        "prescriptions.Medication",
        on_delete=models.PROTECT,
        related_name="prescription_items",
    )
    dose_amount = models.DecimalField(max_digits=10, decimal_places=3)
    dose_unit = models.CharField(max_length=32)
    route = models.CharField(max_length=20, choices=Route.choices)
    frequency_display = models.CharField(max_length=120)
    duration_days = models.PositiveIntegerField()
    instructions = models.TextField(blank=True)
    schedule_type = models.CharField(
        max_length=12,
        choices=ScheduleType.choices,
        default=ScheduleType.SCHEDULED,
    )
    prn_max_per_day = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.medication}: {self.dose_amount} {self.dose_unit}"


class DoseScheduleRule(UUIDTimeStampedModel):
    prescription_item = models.ForeignKey(
        PrescriptionItem,
        on_delete=models.PROTECT,
        related_name="schedule_rules",
    )
    local_time = models.TimeField()
    days_of_week = models.JSONField(default=list, blank=True)
    timezone = models.CharField(max_length=64)

    class Meta:
        ordering = ["local_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["prescription_item", "local_time"],
                name="unique_schedule_time_per_prescription_item",
            )
        ]

    def __str__(self) -> str:
        return f"{self.prescription_item} at {self.local_time}"
