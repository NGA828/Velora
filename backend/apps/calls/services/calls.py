from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.calls.models import CallParticipant, CallSession
from apps.messaging.realtime import publish_user_event
from apps.messaging.selectors import users_may_communicate
from integrations.twilio.config import get_twilio_settings
from integrations.twilio.tokens import twilio_identity


@transaction.atomic
def initiate_call(*, caller, recipient, conversation=None, request=None):
    config = get_twilio_settings()
    if not config.available:
        raise ValidationError("Voice calling is unavailable because Twilio is not configured.")
    patient = conversation.patient if conversation else None
    if (
        conversation
        and not conversation.participants.filter(user=caller, left_at__isnull=True).exists()
    ):
        raise ValidationError("You are not a participant in this conversation.")
    if not users_may_communicate(first=caller, second=recipient, patient=patient):
        raise ValidationError("You are not authorized to call this user.")
    now = timezone.now()
    session = CallSession.objects.create(
        conversation=conversation,
        patient=patient,
        initiated_by=caller,
        initiated_at=now,
    )
    CallParticipant.objects.bulk_create(
        [
            CallParticipant(
                call_session=session,
                user=caller,
                provider_identity=twilio_identity(caller.id),
            ),
            CallParticipant(
                call_session=session,
                user=recipient,
                provider_identity=twilio_identity(recipient.id),
            ),
        ]
    )
    transaction.on_commit(
        lambda: [
            publish_user_event(
                user_id=user_id,
                event_type="call.initiated",
                payload={"call_session_id": str(session.id)},
            )
            for user_id in [caller.id, recipient.id]
        ]
    )
    record_audit_event(
        actor=caller,
        request=request,
        action="calls.session.initiated",
        object_type="calls.CallSession",
        object_id=session.id,
        after={"recipient_id": str(recipient.id)},
    )
    return session


@transaction.atomic
def cancel_call(*, session, actor, request=None):
    locked = CallSession.objects.select_for_update().get(pk=session.pk)
    if not locked.participants.filter(user=actor).exists():
        raise ValidationError("You are not a participant in this call.")
    if locked.status not in {CallSession.Status.QUEUED, CallSession.Status.RINGING}:
        raise ValidationError("This call can no longer be cancelled.")
    locked.status = CallSession.Status.CANCELLED
    locked.ended_at = timezone.now()
    locked.save(update_fields=["status", "ended_at", "updated_at"])
    participant_ids = locked.participants.values_list("user_id", flat=True)
    transaction.on_commit(
        lambda: [
            publish_user_event(
                user_id=user_id,
                event_type="call.updated",
                payload={"call_session_id": str(locked.id), "status": locked.status},
            )
            for user_id in participant_ids
        ]
    )
    return locked
