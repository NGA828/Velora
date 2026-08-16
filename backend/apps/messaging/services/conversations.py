import hashlib
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
    MessageReceipt,
)
from apps.messaging.realtime import publish_user_event
from apps.messaging.selectors import users_may_communicate

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}


@transaction.atomic
def create_direct_conversation(*, creator, participant, patient=None, subject="", request=None):
    if not users_may_communicate(first=creator, second=participant, patient=patient):
        raise ValidationError("You are not authorized to contact this user in this context.")
    existing = (
        Conversation.objects.filter(
            conversation_type=Conversation.Type.DIRECT,
            patient=patient,
            participants__user=creator,
            participants__left_at__isnull=True,
        )
        .filter(
            participants__user=participant,
            participants__left_at__isnull=True,
        )
        .distinct()
        .first()
    )
    if existing and existing.participants.filter(left_at__isnull=True).count() == 2:
        return existing
    now = timezone.now()
    conversation = Conversation.objects.create(
        conversation_type=Conversation.Type.DIRECT,
        patient=patient,
        subject=subject,
        created_by=creator,
    )
    ConversationParticipant.objects.bulk_create(
        [
            ConversationParticipant(conversation=conversation, user=creator, joined_at=now),
            ConversationParticipant(conversation=conversation, user=participant, joined_at=now),
        ]
    )
    record_audit_event(
        actor=creator,
        request=request,
        action="messaging.conversation.created",
        object_type="messaging.Conversation",
        object_id=conversation.id,
        after={
            "participant_id": str(participant.id),
            "patient_id": str(patient.id) if patient else None,
        },
    )
    return conversation


def _validate_attachment(upload):
    if upload.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError("Attachments must not exceed 10 MB.")
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS or upload.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("This attachment type is not allowed.")
    position = upload.tell()
    header = upload.read(16)
    upload.seek(0)
    valid_signature = {
        ".pdf": header.startswith(b"%PDF-"),
        ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": header.startswith(b"\xff\xd8\xff"),
        ".jpeg": header.startswith(b"\xff\xd8\xff"),
    }
    if extension == ".txt":
        try:
            content = upload.read()
            valid_signature[extension] = b"\x00" not in content and bool(
                content.decode("utf-8") or content == b""
            )
        except UnicodeDecodeError:
            valid_signature[extension] = False
        finally:
            upload.seek(0)
    else:
        upload.seek(position)
    if not valid_signature.get(extension, False):
        raise ValidationError("The attachment content does not match its file type.")


@transaction.atomic
def send_message(*, conversation, sender, body, client_message_id, attachment=None, request=None):
    locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
    membership = locked.participants.filter(user=sender, left_at__isnull=True).first()
    if not membership or not locked.is_active:
        raise ValidationError("You are not an active participant in this conversation.")
    body = (body or "").strip()
    if not body and not attachment:
        raise ValidationError("Enter a message or attach a file.")
    if attachment:
        _validate_attachment(attachment)
    existing = Message.objects.filter(sender=sender, client_message_id=client_message_id).first()
    if existing:
        return existing
    message = Message.objects.create(
        conversation=locked,
        sender=sender,
        message_type=Message.Type.ATTACHMENT if attachment else Message.Type.TEXT,
        body=body,
        client_message_id=client_message_id,
        sent_at=timezone.now(),
    )
    if attachment:
        digest = hashlib.sha256()
        for chunk in attachment.chunks():
            digest.update(chunk)
        attachment.seek(0)
        MessageAttachment.objects.create(
            message=message,
            file=attachment,
            original_name=Path(attachment.name).name[:255],
            mime_type=attachment.content_type,
            byte_size=attachment.size,
            checksum=digest.hexdigest(),
        )
    recipients = list(
        locked.participants.filter(left_at__isnull=True)
        .exclude(user=sender)
        .values_list("user_id", flat=True)
    )
    MessageReceipt.objects.bulk_create(
        [MessageReceipt(message=message, recipient_id=user_id) for user_id in recipients]
    )
    locked.updated_at = timezone.now()
    locked.save(update_fields=["updated_at"])
    transaction.on_commit(
        lambda: [
            publish_user_event(
                user_id=user_id,
                event_type="message.created",
                payload={
                    "conversation_id": str(locked.id),
                    "message_id": str(message.id),
                },
            )
            for user_id in {*recipients, sender.id}
        ]
    )
    record_audit_event(
        actor=sender,
        request=request,
        action="messaging.message.sent",
        object_type="messaging.Message",
        object_id=message.id,
        after={
            "conversation_id": str(locked.id),
            "has_attachment": bool(attachment),
        },
    )
    return message


@transaction.atomic
def acknowledge_messages(*, conversation, recipient, up_to_message, seen=False):
    if not conversation.participants.filter(user=recipient, left_at__isnull=True).exists():
        raise ValidationError("You are not an active conversation participant.")
    receipts = MessageReceipt.objects.filter(
        recipient=recipient,
        message__conversation=conversation,
        message__sent_at__lte=up_to_message.sent_at,
    )
    now = timezone.now()
    update = {"delivered_at": now}
    if seen:
        update["seen_at"] = now
    receipts.filter(delivered_at__isnull=True).update(delivered_at=now)
    if seen:
        receipts.filter(seen_at__isnull=True).update(seen_at=now, delivered_at=now)
    sender_ids = set(receipts.values_list("message__sender_id", flat=True))
    transaction.on_commit(
        lambda: [
            publish_user_event(
                user_id=user_id,
                event_type="message.receipt.updated",
                payload={"conversation_id": str(conversation.id)},
            )
            for user_id in sender_ids
        ]
    )
    return now
