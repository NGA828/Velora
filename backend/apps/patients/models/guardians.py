from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import UUIDTimeStampedModel


class GuardianAccess(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        INVITED = "INVITED", "Invited"
        ACTIVE = "ACTIVE", "Active"
        REVOKED = "REVOKED", "Revoked"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="guardian_accesses",
    )
    guardian = models.ForeignKey(
        "identity.PatientGuardProfile",
        on_delete=models.PROTECT,
        related_name="patient_accesses",
        null=True,
        blank=True,
    )
    invitation = models.OneToOneField(
        "identity.Invitation",
        on_delete=models.PROTECT,
        related_name="guardian_access",
    )
    relationship = models.CharField(max_length=80)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.INVITED,
        db_index=True,
    )
    can_view_medical_file = models.BooleanField(default=True)
    can_answer_monitoring = models.BooleanField(default=True)
    can_decide_transfers = models.BooleanField(default=True)
    can_view_billing = models.BooleanField(default=False)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="guardian_accesses_granted",
    )
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "guardian"],
                condition=Q(status="ACTIVE"),
                name="one_active_guardian_link_per_patient_guardian",
            )
        ]

    def __str__(self) -> str:
        return f"{self.patient} — {self.relationship} ({self.status})"
