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
def initiate_call(*, caller, recipient, conversation=None, request=None, provider=None):
    config = get_twilio_settings()
    if provider is None:
        provider = CallSession.Provider.WEBRTC if not config.available else CallSession.Provider.TWILIO
    use_webrtc = provider == CallSession.Provider.WEBRTC
    if not use_webrtc and not config.available:
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
        provider=CallSession.Provider.WEBRTC if use_webrtc else CallSession.Provider.TWILIO,
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


@transaction.atomic
def signal_call(*, session, sender, to_user, data, request=None):
    locked = CallSession.objects.select_for_update().get(pk=session.pk)
    participants = list(locked.participants.values_list("user_id", flat=True))
    if sender.id not in participants:
        raise ValidationError("You are not a participant in this call.")
    if to_user not in participants:
        raise ValidationError("The signaling target is not a participant in this call.")
    if sender.id == to_user:
        raise ValidationError("A call cannot signal itself.")
    transaction.on_commit(
        lambda: publish_user_event(
            user_id=to_user,
            event_type="call.signal",
            payload={
                "call_session_id": str(locked.id),
                "from_user": str(sender.id),
                "data": data,
            },
        )
    )
    record_audit_event(
        actor=sender,
        request=request,
        action="calls.session.signaled",
        object_type="calls.CallSession",
        object_id=locked.id,
        after={"to_user_id": str(to_user), "signal_type": str(data.get("type")) if isinstance(data, dict) else None},
    )
    return locked


@transaction.atomic
def update_call_status(*, session, actor, status, request=None):
    locked = CallSession.objects.select_for_update().get(pk=session.pk)
    if not locked.participants.filter(user=actor).exists():
        raise ValidationError("You are not a participant in this call.")
    valid = {
        CallSession.Status.QUEUED,
        CallSession.Status.RINGING,
        CallSession.Status.IN_PROGRESS,
        CallSession.Status.COMPLETED,
        CallSession.Status.DECLINED,
        CallSession.Status.NO_ANSWER,
        CallSession.Status.FAILED,
        CallSession.Status.CANCELLED,
    }
    if status not in valid:
        raise ValidationError("Unsupported call status.")
    now = timezone.now()
    locked.status = status
    if status == CallSession.Status.RINGING and not locked.ringing_at:
        locked.ringing_at = now
    if status == CallSession.Status.IN_PROGRESS:
        if not locked.ringing_at:
            locked.ringing_at = now
        if not locked.answered_at:
            locked.answered_at = now
        locked.participants.update(status=CallParticipant.Status.CONNECTED, joined_at=now)
    if status in {
        CallSession.Status.COMPLETED,
        CallSession.Status.DECLINED,
        CallSession.Status.NO_ANSWER,
        CallSession.Status.FAILED,
        CallSession.Status.CANCELLED,
    }:
        locked.ended_at = now
        locked.participants.update(status=CallParticipant.Status.LEFT, left_at=now)
    locked.save(update_fields=["status", "ringing_at", "answered_at", "ended_at", "updated_at"])
    participant_ids = list(locked.participants.values_list("user_id", flat=True))
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
    record_audit_event(
        actor=actor,
        request=request,
        action="calls.session.status",
        object_type="calls.CallSession",
        object_id=locked.id,
        after={"status": status},
    )
    return locked
