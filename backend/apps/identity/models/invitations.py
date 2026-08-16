from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimeStampedModel

from .user import UserRole


class Invitation(UUIDTimeStampedModel):
    email = models.EmailField(db_index=True)
    intended_role = models.CharField(max_length=32, choices=UserRole.choices)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField(db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invitations_sent",
    )
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "intended_role"])]

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_pending(self) -> bool:
        return not self.accepted_at and not self.revoked_at and not self.is_expired

    def __str__(self) -> str:
        return f"{self.email} → {self.get_intended_role_display()}"


class LoginOutcome(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS", "Invalid credentials"
    INACTIVE_ACCOUNT = "INACTIVE_ACCOUNT", "Inactive account"
    LOGOUT = "LOGOUT", "Logout"


class LoginEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_events",
    )
    email_attempted = models.EmailField(blank=True)
    outcome = models.CharField(max_length=32, choices=LoginOutcome.choices, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        return f"{self.email_attempted or 'unknown'} — {self.get_outcome_display()}"
