from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.calls.models import CallParticipant, CallSession
from apps.messaging.realtime import publish_user_event
from apps.messaging.selectors import users_may_communicate
from apps.notifications.models import Notification
from apps.notifications.services import notify
from integrations.twilio.config import get_twilio_settings
from integrations.twilio.tokens import twilio_identity

User = get_user_model()


class CallBusyError(Exception):
    """Raised when a call cannot be initiated because either participant is
    already engaged in another call (including a simultaneous same-pair call)."""


@transaction.atomic
def initiate_call(*, caller, recipient, conversation=None, request=None, provider=None):
    config = get_twilio_settings()
    if provider is None:
        provider = (
            CallSession.Provider.WEBRTC
            if not config.available
            else CallSession.Provider.TWILIO
        )
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
    # A participant can be in only one call at a time. Lock both user rows in a
    # stable order so two people calling each other at the same moment are
    # serialized: the earlier session wins and the later caller is told the
    # contact is busy (WhatsApp-style) instead of two parallel sessions ringing
    # at once.
    list(
        User.objects.select_for_update()
        .filter(pk__in=[caller.pk, recipient.pk])
        .order_by("pk")
    )
    active_statuses = {
        CallSession.Status.QUEUED,
        CallSession.Status.RINGING,
        CallSession.Status.IN_PROGRESS,
    }
    active_sessions = CallSession.objects.filter(
        participants__user__in=[caller.pk, recipient.pk],
        status__in=active_statuses,
    ).distinct()
    for session in active_sessions:
        participant_ids = set(session.participants.values_list("user_id", flat=True))
        if caller.pk in participant_ids and recipient.pk in participant_ids:
            if session.initiated_by_id == caller.pk:
                raise CallBusyError(
                    "You already have a call with this contact. Answer it or wait for it to end."
                )
            busy_message = (
                "This contact is calling you. Answer the incoming call instead of "
                "placing a new one."
            )
            raise CallBusyError(busy_message)
        if caller.pk in participant_ids:
            raise CallBusyError("You already have an active call. End it before starting another.")
        raise CallBusyError("The contact is currently in another call. Try again shortly.")
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
                payload={
                    "call_session_id": str(session.id),
                    "initiated_by": str(caller.id),
                },
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
    # Persist the WebRTC offer/answer so the other participant can always
    # recover it from the API, even if the realtime delivery was missed
    # (e.g. they were on another page or their socket was reconnecting).
    if isinstance(data, dict) and data.get("type") == "offer":
        locked.offer_sdp = str(data.get("sdp") or "")
        locked.offer_from = sender
        locked.save(update_fields=["offer_sdp", "offer_from", "updated_at"])
    elif isinstance(data, dict) and data.get("type") == "answer":
        locked.answer_sdp = str(data.get("sdp") or "")
        locked.answer_from = sender
        locked.save(update_fields=["answer_sdp", "answer_from", "updated_at"])
    elif isinstance(data, dict) and data.get("type") == "candidate":
        # Persist candidates so the peer can recover them even when the
        # realtime socket is unavailable. Cap the list to avoid unbounded
        # growth on a noisy/failed negotiation.
        candidates = list(locked.ice_candidates or [])
        candidates.append(
            {
                "from_user": str(sender.id),
                "candidate": data.get("candidate"),
            }
        )
        locked.ice_candidates = candidates[-128:]
        locked.save(update_fields=["ice_candidates", "updated_at"])
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
        after={
            "to_user_id": str(to_user),
            "signal_type": str(data.get("type")) if isinstance(data, dict) else None,
        },
    )
    return locked


@transaction.atomic
def expire_stale_calls(*, max_ring_seconds: int = 45) -> list[CallSession]:
    """Safety net: calls that never left QUEUED/RINGING (e.g. the callee's app
    was closed or the ring was never answered) are marked NO_ANSWER after the
    ring deadline, which also triggers the missed-call notification.

    Called whenever a participant lists calls, so no background worker is
    required; idempotent and safe under concurrency."""
    cutoff = timezone.now() - timedelta(seconds=max_ring_seconds)
    stale = list(
        CallSession.objects.filter(
            status__in=[CallSession.Status.QUEUED, CallSession.Status.RINGING],
            initiated_at__lt=cutoff,
        )
    )
    expired: list[CallSession] = []
    for session in stale:
        try:
            update_call_status(
                session=session,
                actor=session.initiated_by,
                status=CallSession.Status.NO_ANSWER,
            )
        except ValidationError:
            # Another request transitioned the call concurrently; nothing to do.
            continue
        expired.append(session)
    return expired


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
    # A missed call leaves a persistent notification for the callee so they
    # know about it even if they were away from the app (deduped per session).
    if status == CallSession.Status.NO_ANSWER:
        callee = (
            locked.participants.exclude(user=locked.initiated_by)
            .select_related("user")
            .first()
        )
        if callee:
            caller_name = locked.initiated_by.get_full_name()
            notify(
                recipient=callee.user,
                actor=locked.initiated_by,
                category="calls.missed",
                severity=Notification.Severity.WARNING,
                title=f"Missed call from {caller_name}",
                body="You did not answer this call. It was recorded in your call history.",
                route="/calls",
                data={"call_session_id": str(locked.id)},
                dedupe_key=f"call-missed-{locked.id}",
            )
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
