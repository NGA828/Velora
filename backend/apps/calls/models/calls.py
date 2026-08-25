from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class CallSession(UUIDTimeStampedModel):
    class Provider(models.TextChoices):
        TWILIO = "TWILIO", "Twilio"
        WEBRTC = "WEBRTC", "In-app WebRTC"

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RINGING = "RINGING", "Ringing"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        DECLINED = "DECLINED", "Declined"
        NO_ANSWER = "NO_ANSWER", "No answer"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Direction(models.TextChoices):
        OUTBOUND = "OUTBOUND", "Outbound"
        INBOUND = "INBOUND", "Inbound"

    conversation = models.ForeignKey(
        "messaging.Conversation",
        on_delete=models.PROTECT,
        related_name="call_sessions",
        null=True,
        blank=True,
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="call_sessions",
        null=True,
        blank=True,
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="calls_initiated",
    )
    provider = models.CharField(max_length=16, default="TWILIO")
    provider_sid = models.CharField(max_length=80, blank=True, db_index=True)
    direction = models.CharField(
        max_length=12,
        choices=Direction.choices,
        default=Direction.OUTBOUND,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    initiated_at = models.DateTimeField()
    ringing_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=300, blank=True)
    # WebRTC signaling is relayed over the realtime channel, but the offer and
    # answer are also persisted here so a participant who was offline (or on
    # another page when the signal arrived) can recover them when accepting or
    # connecting instead of being stuck with a lost signal.
    offer_sdp = models.TextField(blank=True)
    offer_from = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="call_offers",
        null=True,
        blank=True,
    )
    answer_sdp = models.TextField(blank=True)
    answer_from = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="call_answers",
        null=True,
        blank=True,
    )
    # ICE candidates are persisted alongside the offer/answer so media can
    # still connect when a participant missed the realtime channel delivery
    # (page on another route, transient socket reconnect, or a dropped frame).
    # Each entry is {"from_user": "<uuid>", "candidate": <RTCIceCandidateInit>}.
    ice_candidates = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-initiated_at"]
        indexes = [models.Index(fields=["status", "-initiated_at"])]

    def __str__(self) -> str:
        return f"Call {self.id} ({self.status})"


class CallParticipant(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        INVITED = "INVITED", "Invited"
        RINGING = "RINGING", "Ringing"
        CONNECTED = "CONNECTED", "Connected"
        LEFT = "LEFT", "Left"
        DECLINED = "DECLINED", "Declined"

    call_session = models.ForeignKey(
        CallSession,
        on_delete=models.PROTECT,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="call_participations",
    )
    provider_identity = models.CharField(max_length=120)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.INVITED,
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["call_session", "user"],
                name="unique_call_participant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.call_session_id}"


class CallWebhookEvent(UUIDTimeStampedModel):
    call_session = models.ForeignKey(
        CallSession,
        on_delete=models.PROTECT,
        related_name="webhook_events",
        null=True,
        blank=True,
    )
    provider_event_id = models.CharField(max_length=128, unique=True)
    event_type = models.CharField(max_length=80)
    payload_hash = models.CharField(max_length=64)
    received_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return self.provider_event_id
