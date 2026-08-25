from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class AssistantSession(UUIDTimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_sessions",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="assistant_sessions",
    )
    title = models.CharField(max_length=200, default="Clinical Assistant Session")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "patient", "-updated_at"]),
        ]

    def __str__(self) -> str:
        return f"Assistant Session: {self.user} - {self.patient} ({self.created_at:%Y-%m-%d})"


class AssistantMessage(UUIDTimeStampedModel):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    session = models.ForeignKey(
        AssistantSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER)
    content = models.TextField()
    context_snapshot = models.JSONField(default=dict, blank=True)
    raw_llm_response = models.TextField(blank=True)
    validation_passed = models.BooleanField(default=True)
    validation_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:40]}"


class AssistantAuditLog(UUIDTimeStampedModel):
    session = models.ForeignKey(
        AssistantSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assistant_audit_logs",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="assistant_audit_logs",
    )
    action = models.CharField(max_length=64, default="CHAT_QUERY")
    question = models.TextField()
    response_preview = models.TextField(blank=True)
    recommendation_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=32, default="SUCCESS")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.user} for {self.patient} [{self.status}]"
