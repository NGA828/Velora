from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class MedicationDose(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ADMINISTERED = "ADMINISTERED", "Administered"
        MISSED = "MISSED", "Missed"
        REFUSED = "REFUSED", "Refused"
        CANCELLED = "CANCELLED", "Cancelled"

    prescription_item = models.ForeignKey(
        "prescriptions.PrescriptionItem",
        on_delete=models.PROTECT,
        related_name="doses",
    )
    scheduled_for = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    actual_at = models.DateTimeField(null=True, blank=True)
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medication_doses_actioned",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    due_notification_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["scheduled_for"]
        constraints = [
            models.UniqueConstraint(
                fields=["prescription_item", "scheduled_for"],
                name="unique_scheduled_dose_per_item_time",
            )
        ]
        indexes = [models.Index(fields=["status", "scheduled_for"])]

    def __str__(self) -> str:
        return f"{self.prescription_item} — {self.scheduled_for:%Y-%m-%d %H:%M}"


class MedicationDoseEvent(UUIDTimeStampedModel):
    dose = models.ForeignKey(
        MedicationDose,
        on_delete=models.PROTECT,
        related_name="events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medication_dose_events",
    )
    previous_status = models.CharField(max_length=16, choices=MedicationDose.Status.choices)
    new_status = models.CharField(max_length=16, choices=MedicationDose.Status.choices)
    occurred_at = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["occurred_at", "created_at"]

    def __str__(self) -> str:
        return f"{self.dose}: {self.previous_status} → {self.new_status}"
