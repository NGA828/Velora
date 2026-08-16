from pathlib import Path

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimeStampedModel


def attachment_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()[:12]
    return f"message_attachments/{instance.message.conversation_id}/{instance.id}{suffix}"


class Conversation(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        DIRECT = "DIRECT", "Direct"
        CARE_TEAM = "CARE_TEAM", "Care team"

    conversation_type = models.CharField(
        max_length=16,
        choices=Type.choices,
        default=Type.DIRECT,
    )
    subject = models.CharField(max_length=180, blank=True)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="conversations",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conversations_created",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.subject or f"Conversation {self.id}"


class ConversationParticipant(UUIDTimeStampedModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conversation_memberships",
    )
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="unique_conversation_participant",
            )
        ]
        indexes = [models.Index(fields=["user", "left_at"])]

    def __str__(self) -> str:
        return f"{self.user} in {self.conversation_id}"


class Message(UUIDTimeStampedModel):
    class Type(models.TextChoices):
        TEXT = "TEXT", "Text"
        ATTACHMENT = "ATTACHMENT", "Attachment"
        SYSTEM = "SYSTEM", "System"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="messages_sent",
    )
    message_type = models.CharField(
        max_length=16,
        choices=Type.choices,
        default=Type.TEXT,
    )
    body = models.TextField(blank=True)
    client_message_id = models.CharField(max_length=64)
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="replies",
        null=True,
        blank=True,
    )
    sent_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["sent_at", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "client_message_id"],
                name="unique_sender_client_message_id",
            )
        ]
        indexes = [models.Index(fields=["conversation", "-sent_at"])]

    def __str__(self) -> str:
        return f"{self.sender}: {self.body[:40]}"


class MessageAttachment(UUIDTimeStampedModel):
    message = models.OneToOneField(
        Message,
        on_delete=models.PROTECT,
        related_name="attachment",
    )
    file = models.FileField(upload_to=attachment_upload_path, max_length=300)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    byte_size = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64)

    def __str__(self) -> str:
        return self.original_name


class MessageReceipt(UUIDTimeStampedModel):
    message = models.ForeignKey(
        Message,
        on_delete=models.PROTECT,
        related_name="receipts",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="message_receipts",
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "recipient"],
                name="unique_message_receipt",
            )
        ]
        indexes = [models.Index(fields=["recipient", "seen_at", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.message_id} → {self.recipient_id}"
