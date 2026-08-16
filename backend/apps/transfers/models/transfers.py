from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class TransferRequest(UUIDTimeStampedModel):
    class Urgency(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"
        EMERGENCY = "EMERGENCY", "Emergency"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RECOMMENDED = "RECOMMENDED", "Recommendations generated"
        PENDING_GUARDIAN = "PENDING_GUARDIAN", "Pending Patient Guard"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        FILE_SENT = "FILE_SENT", "Medical file sent"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="transfer_requests",
    )
    care_episode = models.ForeignKey(
        "patients.CareEpisode",
        on_delete=models.PROTECT,
        related_name="transfer_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transfer_requests_created",
    )
    decision_guardian = models.ForeignKey(
        "identity.PatientGuardProfile",
        on_delete=models.PROTECT,
        related_name="transfer_requests",
    )
    selected_hospital = models.ForeignKey(
        "hospital.ExternalHospital",
        on_delete=models.PROTECT,
        related_name="selected_transfer_requests",
        null=True,
        blank=True,
    )
    reason = models.TextField()
    clinical_summary = models.TextField()
    urgency = models.CharField(max_length=16, choices=Urgency.choices)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    recommendation_generation = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    transmitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["patient", "status", "-created_at"])]

    def __str__(self) -> str:
        return f"Transfer {self.id} — {self.patient}"


class TransferRequirement(UUIDTimeStampedModel):
    class RequirementType(models.TextChoices):
        SPECIALTY = "SPECIALTY", "Specialty"
        SERVICE = "SERVICE", "Service"
        CONDITION = "CONDITION", "Clinical condition"

    transfer_request = models.ForeignKey(
        TransferRequest,
        on_delete=models.PROTECT,
        related_name="requirements",
    )
    requirement_type = models.CharField(max_length=16, choices=RequirementType.choices)
    specialty = models.ForeignKey(
        "hospital.Specialty",
        on_delete=models.PROTECT,
        related_name="transfer_requirements",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        "hospital.ServiceDefinition",
        on_delete=models.PROTECT,
        related_name="transfer_requirements",
        null=True,
        blank=True,
    )
    condition = models.ForeignKey(
        "hospital.ClinicalCondition",
        on_delete=models.PROTECT,
        related_name="transfer_requirements",
        null=True,
        blank=True,
    )
    label_snapshot = models.CharField(max_length=180)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_mandatory", "requirement_type", "label_snapshot"]

    def __str__(self) -> str:
        return self.label_snapshot


class TransferRecommendation(UUIDTimeStampedModel):
    transfer_request = models.ForeignKey(
        TransferRequest,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    external_hospital = models.ForeignKey(
        "hospital.ExternalHospital",
        on_delete=models.PROTECT,
        related_name="transfer_recommendations",
    )
    generation = models.PositiveIntegerField()
    eligible = models.BooleanField(default=True)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    rank = models.PositiveIntegerField()
    matched_requirements = models.JSONField(default=list)
    missing_requirements = models.JSONField(default=list)
    explanation = models.TextField()
    generated_at = models.DateTimeField()
    rules_version = models.CharField(max_length=32, default="deterministic-v1")

    class Meta:
        ordering = ["generation", "rank", "external_hospital__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["transfer_request", "external_hospital", "generation"],
                name="unique_transfer_hospital_generation",
            )
        ]

    def __str__(self) -> str:
        return f"{self.external_hospital} — {self.score}%"


class TransferDecision(UUIDTimeStampedModel):
    class Decision(models.TextChoices):
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"

    transfer_request = models.OneToOneField(
        TransferRequest,
        on_delete=models.PROTECT,
        related_name="decision",
    )
    guardian = models.ForeignKey(
        "identity.PatientGuardProfile",
        on_delete=models.PROTECT,
        related_name="transfer_decisions",
    )
    decision = models.CharField(max_length=12, choices=Decision.choices)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.transfer_request_id}: {self.decision}"


class TransferStatusEvent(UUIDTimeStampedModel):
    transfer_request = models.ForeignKey(
        TransferRequest,
        on_delete=models.PROTECT,
        related_name="status_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transfer_status_events",
    )
    previous_status = models.CharField(max_length=24, choices=TransferRequest.Status.choices)
    new_status = models.CharField(max_length=24, choices=TransferRequest.Status.choices)
    reason = models.CharField(max_length=300, blank=True)
    occurred_at = models.DateTimeField()

    class Meta:
        ordering = ["occurred_at", "created_at"]


class TransferTransmission(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    transfer_request = models.ForeignKey(
        TransferRequest,
        on_delete=models.PROTECT,
        related_name="transmissions",
    )
    external_hospital = models.ForeignKey(
        "hospital.ExternalHospital",
        on_delete=models.PROTECT,
        related_name="transfer_transmissions",
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transfer_transmissions_initiated",
    )
    recipient_email = models.EmailField()
    package_storage_key = models.CharField(max_length=300)
    checksum = models.CharField(max_length=64)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.transfer_request_id} → {self.recipient_email}"
