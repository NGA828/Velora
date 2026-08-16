from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class MonitoringThread(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="monitoring_threads",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="monitoring_threads_authored",
    )
    guardian = models.ForeignKey(
        "identity.PatientGuardProfile",
        on_delete=models.PROTECT,
        related_name="monitoring_threads",
    )
    subject = models.CharField(max_length=180)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [models.Index(fields=["patient", "status", "-opened_at"])]

    def __str__(self) -> str:
        return f"{self.patient}: {self.subject}"


class MonitoringQuestion(UUIDTimeStampedModel):
    class ResponseType(models.TextChoices):
        BOOLEAN = "BOOLEAN", "Yes or no"
        TEXT = "TEXT", "Text"
        NUMBER = "NUMBER", "Number"
        SINGLE_CHOICE = "SINGLE_CHOICE", "Single choice"

    thread = models.ForeignKey(
        MonitoringThread,
        on_delete=models.PROTECT,
        related_name="questions",
    )
    prompt = models.TextField()
    response_type = models.CharField(max_length=20, choices=ResponseType.choices)
    options = models.JSONField(default=list, blank=True)
    sequence = models.PositiveIntegerField()
    asked_at = models.DateTimeField()
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sequence", "asked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["thread", "sequence"],
                name="unique_monitoring_question_sequence",
            )
        ]

    def __str__(self) -> str:
        return self.prompt[:80]


class MonitoringResponse(UUIDTimeStampedModel):
    question = models.ForeignKey(
        MonitoringQuestion,
        on_delete=models.PROTECT,
        related_name="responses",
    )
    guardian = models.ForeignKey(
        "identity.PatientGuardProfile",
        on_delete=models.PROTECT,
        related_name="monitoring_responses",
    )
    answer = models.JSONField()
    submitted_at = models.DateTimeField()
    is_current = models.BooleanField(default=True)
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="revisions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["question"],
                condition=models.Q(is_current=True),
                name="one_current_monitoring_response_per_question",
            )
        ]

    def __str__(self) -> str:
        return f"Response to {self.question_id}"
