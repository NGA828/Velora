from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import UUIDTimeStampedModel


class CareEpisode(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        INPATIENT = "INPATIENT", "Inpatient"
        OUTPATIENT = "OUTPATIENT", "Outpatient"
        EMERGENCY = "EMERGENCY", "Emergency"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DISCHARGED = "DISCHARGED", "Discharged"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="care_episodes",
    )
    episode_number = models.CharField(max_length=40, unique=True)
    episode_type = models.CharField(max_length=16, choices=Type.choices)
    department = models.ForeignKey(
        "hospital.Department",
        on_delete=models.PROTECT,
        related_name="care_episodes",
    )
    admission_reason = models.TextField()
    admitted_at = models.DateTimeField()
    discharged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["-admitted_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(discharged_at__isnull=True)
                | Q(discharged_at__gte=models.F("admitted_at")),
                name="care_episode_discharge_after_admission",
            )
        ]

    def __str__(self) -> str:
        return self.episode_number


class PatientCareAssignment(UUIDTimeStampedModel):
    class AssignmentType(models.TextChoices):
        DOCTOR = "DOCTOR", "Doctor"
        NURSE = "NURSE", "Nurse"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="care_assignments",
    )
    care_episode = models.ForeignKey(
        CareEpisode,
        on_delete=models.PROTECT,
        related_name="care_assignments",
    )
    staff = models.ForeignKey(
        "identity.StaffProfile",
        on_delete=models.PROTECT,
        related_name="patient_assignments",
    )
    assignment_type = models.CharField(max_length=12, choices=AssignmentType.choices)
    is_primary = models.BooleanField(default=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="care_assignments_created",
    )

    class Meta:
        ordering = ["-starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gte=models.F("starts_at")),
                name="care_assignment_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["patient", "assignment_type"],
                condition=Q(ends_at__isnull=True, is_primary=True),
                name="one_active_primary_assignment_per_type",
            ),
        ]
        indexes = [
            models.Index(fields=["staff", "assignment_type", "ends_at"]),
            models.Index(fields=["patient", "assignment_type", "ends_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.patient} — {self.staff} ({self.assignment_type})"
